from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from src.tools.order_tool import extract_order_id


@dataclass
class SessionTurn:
    role: str
    content: str


@dataclass
class SessionState:
    session_id: str
    turns: List[SessionTurn] = field(default_factory=list)
    active_order_id: Optional[str] = None
    active_topic: Optional[str] = None
    active_country: Optional[str] = None


class SessionManager:
    """In-memory session manager for tracking multi-turn conversation context."""
    
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    def get_session(self, session_id: str) -> SessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(session_id=session_id)
        return self.sessions[session_id]

    def add_user_message(self, session_id: str, content: str):
        session = self.get_session(session_id)
        session.turns.append(SessionTurn(role="user", content=content))

    def add_assistant_message(self, session_id: str, content: str):
        session = self.get_session(session_id)
        session.turns.append(SessionTurn(role="assistant", content=content))

    def update_context(
        self,
        session_id: str,
        order_id: Optional[str] = None,
        topic: Optional[str] = None,
        country: Optional[str] = None,
    ):
        session = self.get_session(session_id)
        if order_id:
            session.active_order_id = order_id
        if topic:
            session.active_topic = topic
        if country:
            session.active_country = country

    def clear_session(self, session_id: str):
        """Resets/clears session context for testing or session reset."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def resolve_query_context(self, session_id: str, current_query: str) -> Dict[str, Any]:
        """
        Resolves implicit context (order_id, topic, country) for follow-up turns
        and updates active session state.
        """
        session = self.get_session(session_id)
        query_lower = current_query.lower()
        
        # 1. Order ID resolution
        extracted_id = extract_order_id(current_query)
        if extracted_id:
            session.active_order_id = extracted_id
        resolved_order_id = session.active_order_id
        
        # 2. International shipping follow-up resolution
        if "canada" in query_lower:
            session.active_country = "Canada"
        resolved_country = session.active_country
            
        if "internationally" in query_lower or "international" in query_lower:
            session.active_topic = "international_shipping"
        elif "shipping" in query_lower or "ship" in query_lower:
            session.active_topic = "shipping"
        elif "return" in query_lower:
            session.active_topic = "returns"
        elif "warranty" in query_lower:
            session.active_topic = "warranty"
            
        resolved_topic = session.active_topic

        return {
            "resolved_order_id": resolved_order_id,
            "resolved_topic": resolved_topic,
            "resolved_country": resolved_country,
            "has_order_history": bool(session.active_order_id),
            "previous_turns": session.turns,
        }
