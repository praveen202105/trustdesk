from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from trustdesk.jobs import Completion, TransientError, claim, complete, enqueue, run_once
from trustdesk.models import Job, now


def queue(database):
    with database.begin() as session:
        return enqueue(session, "test")["job_id"]


def test_claim_is_exclusive_and_fenced(database):
    job_id = queue(database)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: claim(database), range(2)))
    claims = [result for result in results if result]
    assert len(claims) == 1
    original = claims[0]
    with database.begin() as session:
        session.get(Job, job_id).lease_until = now() - timedelta(seconds=1)
    recovered = claim(database)
    assert recovered["owner"] != original["owner"]
    assert not complete(original, Completion({"bad": True}), database)
    assert complete(recovered, Completion({"recovered": True}), database)
    with database() as session:
        assert session.get(Job, job_id).result == {"recovered": True}


def test_retry_is_bounded_and_persisted(database):
    job_id = queue(database)
    def failed(job, factory):
        raise TransientError("temporary")
    for index in range(3):
        assert run_once(database, failed)
        with database.begin() as session:
            job = session.get(Job, job_id)
            assert job.attempts == index + 1
            job.available_at = now() - timedelta(seconds=1)
    with database() as session:
        assert session.get(Job, job_id).status == "failed"


def test_completion_is_atomic(database):
    job_id = queue(database)
    def good(job, factory):
        return Completion({"ready": True})
    assert run_once(database, good)
    assert not run_once(database, good)
    with database() as session:
        assert session.get(Job, job_id).status == "succeeded"
