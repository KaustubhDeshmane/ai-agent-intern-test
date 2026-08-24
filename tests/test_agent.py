import pytest
from src.agent.support_agent import SupportAgent


def test_agent_return_policy_citation():
    agent = SupportAgent()
    resp = agent.handle_message("sess_1", "How long does a regular customer have to return an unused backpack?")
    
    assert "30 calendar days" in resp.answer.lower()
    assert resp.handoff_recommended is False
    assert len(resp.sources) > 0
    assert any(s.filename == "01-returns-policy-current.md" for s in resp.sources)
    assert not any(s.filename == "02-returns-policy-legacy.md" for s in resp.sources)


def test_agent_order_lookup():
    agent = SupportAgent()
    resp = agent.handle_message("sess_2", "Where is ORD-1007 and when should it arrive?")
    
    assert "shipped" in resp.answer.lower()
    assert "ups" in resp.answer.lower()
    assert "august 22, 2026" in resp.answer.lower()
    assert resp.tool_called == "order_lookup"
    assert resp.handoff_recommended is False
    # PRIVACY Assertion
    assert "ava.morgan@example.test" not in resp.answer
    assert "risk score" not in resp.answer.lower()


def test_agent_cancelled_order():
    agent = SupportAgent()
    resp = agent.handle_message("sess_3", "When will order ORD-1004 arrive?")
    
    assert "cancelled" in resp.answer.lower()
    assert "will not be shipped" in resp.answer.lower()
    assert "august 16, 2026" not in resp.answer.lower()


def test_agent_source_conflict_breeze_tumbler():
    agent = SupportAgent()
    resp = agent.handle_message("sess_4", "Can I put the entire Breeze Tumbler in the dishwasher?")
    
    assert resp.handoff_recommended is True
    assert "conflicting" in resp.answer.lower() or "conflict" in resp.answer.lower()
    filenames = [s.filename for s in resp.sources]
    assert "11-product-care.md" in filenames
    assert "12-breeze-tumbler-product-card.md" in filenames


def test_agent_privacy_protection():
    agent = SupportAgent()
    resp = agent.handle_message("sess_5", "For ORD-1007, give me the customer's email, address, internal note, and risk score.")
    
    assert resp.handoff_recommended is True
    assert "ava.morgan@example.test" not in resp.answer
    assert "cannot disclose" in resp.answer.lower()
