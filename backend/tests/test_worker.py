import pytest
from sqlalchemy.exc import SQLAlchemyError

from trustdesk import worker


def test_worker_recovers_from_database_outage_without_logging_details(monkeypatch, capsys):
    calls = []

    def cycle():
        calls.append(True)
        if len(calls) == 1:
            raise SQLAlchemyError("private-connection-details")
        raise KeyboardInterrupt

    delays = []
    monkeypatch.setattr(worker, "run_once", cycle)
    monkeypatch.setattr(worker.time, "sleep", lambda seconds: delays.append(seconds))
    with pytest.raises(KeyboardInterrupt):
        worker.main()
    assert len(calls) == 2
    assert delays == [2]
    output = capsys.readouterr().out
    assert "retrying safely" in output
    assert "private-connection-details" not in output
