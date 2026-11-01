from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import func, literal_column, select

from .config import settings
from .ingest import checksum
from .models import Chunk, Document
from .providers import embedding


def embedding_version() -> str:
    return f"{settings.embedding_provider}:{settings.embedding_model}:{settings.embedding_dimension}"


def index_knowledge(session) -> int:
    count = 0
    for doc in session.scalars(select(Document).order_by(Document.id)):
        # Keep vendor material stored for audit, but do not embed or retrieve unapproved instructions.
        if not doc.trusted_policy:
            continue
        chunks: list[str] = []
        current = ""
        for paragraph in doc.content.split("\n\n"):
            if current and len(current) + len(paragraph) > 1500:
                chunks.append(current)
                current = ""
            current += ("\n\n" if current else "") + paragraph
        if current:
            chunks.append(current)
        for index, content in enumerate(chunks):
            chunk_id = checksum([doc.id, doc.checksum, index])
            session.merge(Chunk(id=chunk_id, document_id=doc.id, version_hash=doc.checksum,
                                content=content, embedding=embedding(content), embedding_model=embedding_version()))
            count += 1
    session.flush()
    return count


def retrieve(session, query: str) -> list[dict]:
    query_vector = embedding(query)
    eligible = (Document.trusted_policy.is_(True), Chunk.version_hash == Document.checksum,
                Chunk.embedding_model == embedding_version(), Chunk.embedding.is_not(None))
    base = select(Chunk).join(Document).where(*eligible)
    chunks = session.scalars(base).all()
    trusted_count = session.scalar(select(func.count()).select_from(Document).where(Document.trusted_policy.is_(True)))
    if not chunks or len({x.document_id for x in chunks}) != trusted_count:
        raise HTTPException(503, "RETRIEVAL_UNAVAILABLE")
    if any(len(c.embedding) != settings.embedding_dimension for c in chunks):
        raise HTTPException(503, "EMBEDDING_DIMENSION_MISMATCH")
    text_vector = func.to_tsvector(literal_column("'english'"), Chunk.content)
    text_query = func.plainto_tsquery(literal_column("'english'"), query)
    lexical = session.scalars(base.order_by(func.ts_rank(text_vector, text_query).desc(), Chunk.id).limit(12)).all()
    semantic = session.scalars(base.order_by(Chunk.embedding.cosine_distance(query_vector), Chunk.id).limit(12)).all()
    scores: dict[str, float] = defaultdict(float)
    by_id = {c.id: c for c in chunks}
    for ranked in (lexical, semantic):
        for rank, chunk in enumerate(ranked, start=1):
            scores[chunk.id] += 1 / (60 + rank)
    selected = []
    per_doc: dict[str, int] = defaultdict(int)
    budget = 32000  # Conservative character cap, additionally bounded by six 1500-character chunks.
    for key in sorted(scores, key=lambda key: (-scores[key], key)):
        chunk = by_id[key]
        if per_doc[chunk.document_id] >= 2 or len(chunk.content) > budget:
            continue
        selected.append({"document_id": chunk.document_id, "version_hash": chunk.version_hash,
                         "chunk_id": chunk.id, "quote": chunk.content, "score": scores[key]})
        budget -= len(chunk.content)
        per_doc[chunk.document_id] += 1
        if len(selected) == 6:
            break
    return selected


def valid_citations(session, citations: list[dict], retrieved: list[dict]) -> bool:
    allowed = {item["chunk_id"] for item in retrieved}
    for citation in citations:
        chunk = session.get(Chunk, citation.get("chunk_id"))
        doc = session.get(Document, citation.get("document_id"))
        if not chunk or not doc or not doc.trusted_policy or chunk.id not in allowed:
            return False
        if (chunk.document_id != doc.id or chunk.version_hash != doc.checksum or
                citation.get("version_hash") != chunk.version_hash or not citation.get("quote") or
                citation["quote"] not in chunk.content):
            return False
    return True
