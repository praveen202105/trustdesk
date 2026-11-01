import pytest
from fastapi import HTTPException

from trustdesk.knowledge import index_knowledge, retrieve, valid_citations
from trustdesk.models import Document


def test_hybrid_retrieval_and_evidence(database):
    with database.begin() as session:
        assert index_knowledge(session) >= 7
        results = retrieve(session, "damaged defective item refund replacement return window")
        assert "KB-REFUND-001" in {c["document_id"] for c in results}
        assert "KB-ADVERSARIAL-001" not in {c["document_id"] for c in results}
        citation = {**results[0], "claim": "Policy excerpt"}
        assert valid_citations(session, [citation], results)
        citation["quote"] = "Invented policy"
        assert not valid_citations(session, [citation], results)
        citation["document_id"] = "KB-ADVERSARIAL-001"
        assert not valid_citations(session, [citation], results)


def test_missing_or_stale_index_fails_explicitly(database):
    with database.begin() as session:
        with pytest.raises(HTTPException):
            retrieve(session, "refund")
        index_knowledge(session)
        session.get(Document, "KB-REFUND-001").checksum = "changed"
        session.flush()
        with pytest.raises(HTTPException):
            retrieve(session, "refund")
