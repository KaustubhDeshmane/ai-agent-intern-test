from src.config import KNOWLEDGE_BASE_DIR
from src.rag.document_parser import parse_document_file
from src.rag.chunker import chunk_document, load_and_chunk_all
from src.rag.precedence import filter_authoritative_chunks, detect_source_conflicts
from src.rag.retriever import KnowledgeBaseRetriever


def test_parse_front_matter_current():
    filepath = KNOWLEDGE_BASE_DIR / "01-returns-policy-current.md"
    meta, body = parse_document_file(filepath)
    assert meta.document_id == "RET-2026-01"
    assert meta.title == "Returns Policy"
    assert meta.status == "active"
    assert meta.policy_authority == "official"
    assert meta.audience == "customer"
    assert meta.supersedes == "RET-2024-01"
    assert "Standard return window" in body


def test_parse_front_matter_legacy():
    filepath = KNOWLEDGE_BASE_DIR / "02-returns-policy-legacy.md"
    meta, body = parse_document_file(filepath)
    assert meta.document_id == "RET-2024-01"
    assert meta.status == "superseded"
    assert meta.superseded_by == "RET-2026-01"


def test_parse_front_matter_migration_scratchpad():
    filepath = KNOWLEDGE_BASE_DIR / "14-internal-content-migration-notes.md"
    meta, body = parse_document_file(filepath)
    assert meta.document_id == "MIG-TEST-04"
    assert meta.status == "draft"
    assert meta.policy_authority == "none"
    assert meta.customer_answering is False
    assert meta.audience == "internal"


def test_chunker_preserves_metadata():
    filepath = KNOWLEDGE_BASE_DIR / "01-returns-policy-current.md"
    chunks = chunk_document(filepath)
    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert first_chunk.filename == "01-returns-policy-current.md"
    assert first_chunk.doc_id == "RET-2026-01"
    assert first_chunk.metadata.status == "active"


def test_precedence_filtering():
    all_chunks = load_and_chunk_all(KNOWLEDGE_BASE_DIR)
    auth_chunks = filter_authoritative_chunks(all_chunks, allow_legacy=False)
    
    filenames = {c.filename for c in auth_chunks}
    assert "01-returns-policy-current.md" in filenames
    # Superseded and draft scratchpad should be excluded from authoritative chunks
    assert "02-returns-policy-legacy.md" not in filenames
    assert "14-internal-content-migration-notes.md" not in filenames


def test_conflict_detection_breeze_tumbler():
    retriever = KnowledgeBaseRetriever()
    chunks = retriever.retrieve("Can I put the entire Breeze Tumbler in the dishwasher?", top_k=10)
    has_conflict, msg, conf_chunks = detect_source_conflicts("Can I put the entire Breeze Tumbler in the dishwasher?", chunks)
    
    assert has_conflict is True
    assert msg is not None
    assert "11-product-care.md" in [c.filename for c in conf_chunks]
    assert "12-breeze-tumbler-product-card.md" in [c.filename for c in conf_chunks]


def test_retriever_standard_return():
    retriever = KnowledgeBaseRetriever()
    results = retriever.retrieve("How long does a regular customer have to return an unused backpack?")
    assert len(results) > 0
    top_filenames = [r.filename for r in results]
    assert "01-returns-policy-current.md" in top_filenames
    assert "02-returns-policy-legacy.md" not in top_filenames
    assert "14-internal-content-migration-notes.md" not in top_filenames
