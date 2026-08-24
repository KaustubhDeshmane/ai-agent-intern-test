from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    document_id: str
    title: str
    status: str  # active, superseded, draft
    effective_date: Optional[str] = None
    last_reviewed: Optional[str] = None
    audience: Optional[str] = "customer"  # customer, internal
    policy_authority: Optional[str] = "official"  # official, none
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    customer_answering: bool = True


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    title: str
    heading: str
    content: str
    metadata: DocumentMetadata
    score: float = 0.0


class OrderItem(BaseModel):
    sku: Optional[str] = None
    name: str
    quantity: int
    final_sale: bool = False


class OrderResult(BaseModel):
    found: bool = True
    order_id: str
    membership_tier: Optional[str] = None
    items: List[OrderItem] = Field(default_factory=list)
    placed_at: Optional[str] = None
    status: str
    status_updated_at: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[str] = None
    customer_safe_message: Optional[str] = None
    message: Optional[str] = None
    handoff_recommended: bool = False


class SourceCitation(BaseModel):
    filename: str
    heading: str
    title: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.filename} ({self.heading})"


class AgentResponse(BaseModel):
    answer: str
    sources: List[SourceCitation] = Field(default_factory=list)
    handoff_recommended: bool = False
    tool_called: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    debug_trace: Optional[Dict[str, Any]] = None
