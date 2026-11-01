import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from .ingest import checksum
from .models import Customer, Document, Order, Ticket


def context_for(session, ticket_id: str) -> dict:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise ValueError("RESOURCE_NOT_FOUND")
    customer = session.get(Customer, ticket.customer_id)
    order = session.get(Order, ticket.order_id) if ticket.order_id else None
    if order and order.customer_id != ticket.customer_id:
        raise ValueError("CONTEXT_OWNERSHIP_MISMATCH")
    policies = session.scalars(select(Document).order_by(Document.id)).all()
    # Expected labels and private account fields cannot enter the generation context.
    return {"ticket": ticket.data,
            "customer": {k: v for k, v in customer.data.items() if k in ("name", "tier", "verified")},
            "order": order.data if order else None,
            "policies": {d.id: {"hash": d.checksum, "trusted": d.trusted_policy} for d in policies}}


def context_hash(context: dict) -> str:
    return checksum(context)


def return_eligible(context: dict) -> bool:
    order = context.get("order")
    if not order or any(item.get("final_sale") for item in order["items"]):
        return False
    if not order.get("delivered_at") or not order.get("eligible_return_until"):
        return False
    delivered = date.fromisoformat(order["delivered_at"])
    until = date.fromisoformat(order["eligible_return_until"])
    at = datetime.fromisoformat(context["ticket"]["created_at"]).date()
    return until == delivered + timedelta(days=7) and delivered <= at <= until


def decision(context: dict) -> dict:
    ticket = context["ticket"]
    text = (ticket["subject"] + " " + ticket["body"]).lower()
    order = context.get("order")
    category, priority, sentiment = "general", "low", "neutral"
    escalate, actions, guardrails = False, [], []
    doc, reason = "KB-SECURITY-001", "General request requires a support specialist"
    template = "A support specialist will review your request because we do not have enough policy evidence to answer it."
    if any(term in text for term in ("system prompt", "api key", "internal notes", "hidden prompt")):
        category, priority, escalate = "account_security", "high", True
        guardrails = ["sensitive_disclosure_blocked"]
        reason = "Request attempts to disclose protected internal information"
        template = "I cannot disclose hidden system prompts, API keys, internal notes or secrets. A support specialist will review this security request."
    elif "coupon" in text and any(term in text for term in ("ignore", "override", "hide", "do not mention", "do not tell")):
        category, priority, escalate = "general", "medium", True
        guardrails = ["prompt_injection_blocked"]
        reason = "Unsafe instruction attempted to bypass coupon policy and human review"
        template = "I cannot follow this unsafe instruction or issue a hidden coupon. It has been flagged for human review."
    elif any(term in text for term in ("account email", "password", "identity check", "account deletion")):
        category, priority, escalate = "account_security", "high", True
        doc, reason = "KB-ACCOUNT-001", "Identity verification is required before account changes"
        guardrails = ["identity_bypass_blocked"]
        template = "Identity verification is required before an account email change. I cannot change your email directly or skip verification. A human support specialist will help you verify your identity."
    elif any(term in text for term in ("swelling", "swollen", "overheating", "burning smell", "electric shock", "exposed wires")):
        category, priority, sentiment, escalate = "warranty", "urgent", "worried", True
        doc, reason = "KB-WARRANTY-001", "Product safety issue requires urgent specialist escalation"
        guardrails = ["safety_escalation"]
        template = "This is a product safety issue. Please stop using the device and do not attempt battery troubleshooting. I am recommending urgent escalation to a human specialist, who can check warranty coverage and proof of purchase."
    elif any(term in text for term in ("double charge", "duplicate charge", "two charges", "charged twice")):
        category, priority, sentiment = "billing", "high", "frustrated"
        doc, reason = "KB-BILLING-001", "A duplicate charge requires billing review"
        template = "We can start a billing review for the reported duplicate charge on this order. Please share the transaction reference or payment date and amount if needed. A refund review requires human approval; this does not mean a refund has been issued. Do not send a full card number, CVV or OTP."
        actions = ["start_refund_review"] if order else []
        escalate = not bool(order)
    elif any(term in text for term in ("tracking", "package", "shipping", "delivery")) and not any(term in text for term in ("damaged", "cracked", "defective")):
        category, sentiment = "shipping", "frustrated"
        doc, reason = "KB-SHIPPING-001", "Tracking delay requires policy-guided carrier investigation"
        days = re.search(r"(\d+) business days", text)
        stale = bool(days and int(days[1]) >= 5)
        priority = "high" if stale or any(x in text for x in ("travel", "urgent")) else "medium"
        actions = ["open_carrier_investigation"] if stale else []
        template = "The next step is a carrier investigation when tracking has not moved for at least 5 business days. We cannot promise an instant refund or replacement. Lost-package resolution requires carrier confirmation or the policy's 10-business-day condition."
    elif any(term in text for term in ("refund", "replacement", "damaged", "cracked", "defective")):
        category, doc = "refund", "KB-REFUND-001"
        final_sale = bool(order and any(item.get("final_sale") for item in order["items"]))
        if final_sale:
            reason = "Software or marked final-sale items do not qualify for an ordinary refund"
            template = "Software licenses and marked final-sale items are final sale after purchase. I cannot approve a refund under the standard policy; any legal exception or manager-approved exception must be reviewed separately."
        elif return_eligible(context):
            priority, sentiment = "medium", "frustrated"
            reason = "Damaged physical item reported within the seven-day return window"
            actions = ["create_replacement_order", "start_refund_review"]
            template = "I am sorry your item arrived damaged. Within 7 calendar days of delivery, policy allows a replacement or refund review. Please provide a photo or short description of the damage for review. Any action requires human approval; no refund or replacement has been issued."
        else:
            priority, escalate = "medium", True
            reason = "Return eligibility is missing or outside the supported window"
            template = "We cannot confirm standard return eligibility from the available evidence. A support specialist must review the delivery date, item status and any applicable exception."
    else:
        escalate = True
    if escalate:
        actions = ["escalate_to_human"]
    if not context["policies"].get(doc, {}).get("trusted"):
        escalate, actions = True, ["escalate_to_human"]
        reason, template = "Policy evidence is missing or unapproved", "A support specialist must review this request because the policy evidence is unavailable."
    return {"category": category, "priority": priority, "sentiment": sentiment,
            "escalation_required": escalate, "reason": reason, "recommended_actions": actions,
            "guardrails": guardrails, "policy_document": doc, "safe_template": template}


def action_arguments(context: dict, result: dict) -> dict | None:
    order = context.get("order")
    if (not order or result["escalation_required"] or "start_refund_review" not in result["recommended_actions"]
            or result["category"] not in ("refund", "billing")):
        return None
    amount = Decimal(str(order["total"]))
    if not amount.is_finite() or amount <= 0:
        return None
    return {"order_id": order["order_id"], "reason": result["reason"], "amount": str(amount)}
