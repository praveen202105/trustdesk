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
