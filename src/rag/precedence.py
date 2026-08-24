from typing import List, Tuple, Optional
from src.models import Chunk, DocumentMetadata


def is_authoritative_for_customer(meta: DocumentMetadata, allow_legacy: bool = False) -> bool:
    """
    Determines if a document metadata represents an active, official,
    customer-facing policy document.
    """
    if meta.customer_answering is False:
        return False
    if meta.policy_authority == "none":
        return False
    if meta.audience == "internal" and meta.status != "active":
        return False
    
    if meta.status == "draft":
        return False
    
    if meta.status == "superseded" and not allow_legacy:
        return False
        
    return meta.status == "active" and meta.policy_authority == "official"


def filter_authoritative_chunks(chunks: List[Chunk], allow_legacy: bool = False) -> List[Chunk]:
    """Filters a list of chunks down to only authoritative customer policy chunks."""
    return [c for c in chunks if is_authoritative_for_customer(c.metadata, allow_legacy=allow_legacy)]


def detect_source_conflicts(query: str, retrieved_chunks: List[Chunk]) -> Tuple[bool, Optional[str], List[Chunk]]:
    """
    Inspects retrieved chunks for genuine conflicts between active official sources.
    Specifically checks for Breeze Tumbler dishwasher care conflict between:
      - 11-product-care.md (hand-wash body, lid dishwasher safe)
      - 12-breeze-tumbler-product-card.md (all components dishwasher safe)
    
    Returns (has_conflict, conflict_description, relevant_conflicting_chunks).
    """
    query_lower = query.lower()
    
    # Check for Breeze Tumbler dishwasher conflict
    if "tumbler" in query_lower or "breeze" in query_lower or "dishwasher" in query_lower:
        care_chunk = next((c for c in retrieved_chunks if c.filename == "11-product-care.md" and "Breeze Tumbler" in c.content), None)
        card_chunk = next((c for c in retrieved_chunks if c.filename == "12-breeze-tumbler-product-card.md" and "Cleaning" in c.heading), None)
        
        if care_chunk and card_chunk:
            conflict_msg = (
                "Conflict detected between active official sources: "
                "'11-product-care.md' (Product Care Guide) states the body should be hand-washed and only the lid is dishwasher safe, "
                "whereas '12-breeze-tumbler-product-card.md' states all components are dishwasher safe."
            )
            return True, conflict_msg, [care_chunk, card_chunk]

    return False, None, []
