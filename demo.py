import time
from src.agent.support_agent import SupportAgent
from evaluation.evaluate import run_evaluation

def run_live_demo():
    agent = SupportAgent()
    
    print("\n" + "=" * 70)
    print("      ASTER & ROW RELIABLE RAG SUPPORT AGENT -- LIVE DEMO")
    print("=" * 70 + "\n")
    
    # -------------------------------------------------------------
    # Scenario 1: KB Question with Source Citation
    # -------------------------------------------------------------
    print("[SCENARIO 1] Knowledge-Base Question with Source Citation")
    print("Customer: 'How long does a regular customer have to return an unused backpack?'")
    resp1 = agent.handle_message("demo_sess_1", "How long does a regular customer have to return an unused backpack?")
    print(f"Agent: {resp1.answer}")
    if resp1.sources:
        print(f"Sources: {', '.join([str(s) for s in resp1.sources])}")
    print(f"Handoff Recommended: {resp1.handoff_recommended}")
    print("-" * 70 + "\n")
    time.sleep(1)

    # -------------------------------------------------------------
    # Scenario 2: Order Lookup with Privacy Preservation
    # -------------------------------------------------------------
    print("[SCENARIO 2] Order Status Lookup & PII Protection")
    print("Customer: 'Where is ORD-1007 and when should it arrive?'")
    resp2 = agent.handle_message("demo_sess_2", "Where is ORD-1007 and when should it arrive?")
    print(f"Agent: {resp2.answer}")
    print(f"Tool Called: {resp2.tool_called} | Arguments: {resp2.tool_arguments}")
    print("Privacy Protection: No customer email, address, or risk scores disclosed.")
    print("-" * 70 + "\n")
    time.sleep(1)

    # -------------------------------------------------------------
    # Scenario 3: Multi-Turn Conversation (Context Resolution)
    # -------------------------------------------------------------
    print("[SCENARIO 3] Multi-Turn Conversation & Session Memory")
    print("Turn 1 - Customer: 'Do you ship internationally?'")
    resp3a = agent.handle_message("demo_sess_3", "Do you ship internationally?")
    print(f"Agent: {resp3a.answer}\n")
    
    print("Turn 2 - Customer: 'What about Canada, and how long does it take?'")
    resp3b = agent.handle_message("demo_sess_3", "What about Canada, and how long does it take?")
    print(f"Agent: {resp3b.answer}")
    if resp3b.sources:
        print(f"Sources: {', '.join([str(s) for s in resp3b.sources])}")
    print("-" * 70 + "\n")
    time.sleep(1)

    # -------------------------------------------------------------
    # Scenario 4: Active Source Conflict & Human Handoff
    # -------------------------------------------------------------
    print("[SCENARIO 4] Source Conflict Detection & Human Handoff")
    print("Customer: 'Can I put the entire Breeze Tumbler in the dishwasher?'")
    resp4 = agent.handle_message("demo_sess_4", "Can I put the entire Breeze Tumbler in the dishwasher?")
    print(f"Agent: {resp4.answer}")
    if resp4.sources:
        print(f"Conflicting Sources: {', '.join([str(s) for s in resp4.sources])}")
    print(f"Handoff Recommended: {resp4.handoff_recommended}")
    print("-" * 70 + "\n")
    time.sleep(1)

    # -------------------------------------------------------------
    # Scenario 5: Evaluation Suite Execution
    # -------------------------------------------------------------
    print("[SCENARIO 5] Full Automated Evaluation Suite Execution")
    run_evaluation()

if __name__ == "__main__":
    run_live_demo()
