import pytest
from src.agent.session import SessionManager


def test_session_order_followup():
    sm = SessionManager()
    session_id = "sess_test_1"
    
    # Turn 1: User mentions ORD-1007
    sm.add_user_message(session_id, "Where is ORD-1007?")
    sm.update_context(session_id, order_id="ORD-1007")
    sm.add_assistant_message(session_id, "Order ORD-1007 has shipped with UPS.")
    
    # Turn 2: User asks follow-up without order ID
    ctx = sm.resolve_query_context(session_id, "When will it arrive?")
    assert ctx["resolved_order_id"] == "ORD-1007"
    assert ctx["has_order_history"] is True


def test_session_canada_followup():
    sm = SessionManager()
    session_id = "sess_test_2"
    
    sm.add_user_message(session_id, "Do you ship internationally?")
    ctx1 = sm.resolve_query_context(session_id, "Do you ship internationally?")
    sm.update_context(session_id, topic=ctx1["resolved_topic"])
    
    ctx2 = sm.resolve_query_context(session_id, "What about Canada, and how long does it take?")
    assert ctx2["resolved_country"] == "Canada"
    assert ctx2["resolved_topic"] in ("international_shipping", "shipping")


def test_session_isolation():
    sm = SessionManager()
    sm.update_context("session_a", order_id="ORD-1001")
    sm.update_context("session_b", order_id="ORD-1002")
    
    ctx_a = sm.resolve_query_context("session_a", "When will it arrive?")
    ctx_b = sm.resolve_query_context("session_b", "When will it arrive?")
    
    assert ctx_a["resolved_order_id"] == "ORD-1001"
    assert ctx_b["resolved_order_id"] == "ORD-1002"
