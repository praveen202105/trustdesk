import copy

from trustdesk.policy import action_arguments, context_for, decision, return_eligible


def test_return_boundary_is_historical_and_final_sale_is_blocked(database):
    with database() as session:
        context=context_for(session,"tkt_9001")
        assert return_eligible(context)
        for day, expected in (("2026-07-01T23:59:00+05:30",True),("2026-07-02T00:00:00+05:30",False)):
            changed=copy.deepcopy(context)
            changed["ticket"]["created_at"]=day
            assert return_eligible(changed) is expected
        final=context_for(session,"tkt_9003")
        assert not return_eligible(final)
        assert action_arguments(final,decision(final)) is None


def test_gold_warranty_and_unknown_item_conditions(database):
    from trustdesk.policy import warranty_eligible
    with database() as session:
        gold=context_for(session,"tkt_9004")
        assert warranty_eligible(gold) is True
        standard=copy.deepcopy(gold)
        standard["customer"]["tier"]="standard"
        assert warranty_eligible(standard) is False
        unknown=context_for(session,"tkt_9001")
        unknown["ticket"]={**unknown["ticket"],"subject":"Refund please","body":"Please refund my item."}
        assert decision(unknown)["escalation_required"]
        assert not action_arguments(unknown,decision(unknown))
