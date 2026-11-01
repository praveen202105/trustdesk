import json
import shutil
from pathlib import Path

import pytest
from sqlalchemy import func, select

from trustdesk.ingest import ingest
from trustdesk.models import Customer, Document, Order, Ticket

SOURCE = Path(__file__).resolve().parents[2] / "capstone/data"


def test_import_repeat_and_label_isolation(database):
    with database.begin() as session:
        ingest(session, SOURCE)
        for model, count in ((Customer, 6), (Order, 6), (Ticket, 8), (Document, 8)):
            assert session.scalar(select(func.count()).select_from(model)) == count
        ticket = session.get(Ticket, "tkt_9008")
        assert not any(k.startswith("expected_") for k in ticket.data)
        assert ticket.created_at.year == 2026


@pytest.mark.parametrize("fault", ["ownership", "timestamp", "duplicate"])
def test_invalid_import_is_atomic(database, tmp_path, fault):
    shutil.copytree(SOURCE, tmp_path / "data")
    path = tmp_path / "data/tickets.json"
    tickets = json.loads(path.read_text())
    if fault == "ownership":
        tickets[-1]["customer_id"] = "cus_1001"
    elif fault == "timestamp":
        tickets[-1]["created_at"] = "invalid"
    else:
        tickets.append(tickets[0])
    path.write_text(json.dumps(tickets))
    with pytest.raises(ValueError), database.begin() as session:
        ingest(session, tmp_path / "data")
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Ticket)) == 8
        assert session.get(Ticket, "tkt_9008").customer_id == "cus_1006"
