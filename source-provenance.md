# Source provenance

Upstream: https://github.com/airtribe-projects/trustdesk-capstone
Verified source commit: `01adf207f691c9e54587057ca77371ead90a082e`.
The capstone/ directory preserves the fictional source dataset, original documentation and validation utilities. No upstream license was present; this application does not relicense the supplied pack.

Verified differences from initial design:
- Source IDs are `cus_*`, `ord_*`, `tkt_*` and `KB-*`.
- Refund review payload requires order_id, reason, amount and idempotency_key; allowed categories are refund and billing.
- Expected labels are evaluation-only. Strip them from imported runtime tickets and never pass eval expectations to generation.
- The source contract permits documented route-shape changes. Local APIs retain /api/v1 and async jobs; triage also includes sentiment.
- Source evaluation citation coverage means all required document IDs appear; report this separately from claim grounding.
- Other catalog actions may be recommendations; only start_refund_review is executable in V1.
