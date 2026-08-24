import sys
import argparse
from pathlib import Path
from src.agent.support_agent import SupportAgent
from evaluation.evaluate import run_evaluation


def interactive_cli(debug: bool = False):
    agent = SupportAgent(debug_mode=debug)
    session_id = "cli_session_1"
    
    print("=" * 60)
    print("Aster & Row Reliable RAG Support Agent")
    print("Type your query below. Type 'exit' or 'quit' to end session.")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("Customer: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
                
            response = agent.handle_message(session_id, user_input)
            
            print(f"\nAgent: {response.answer}")
            if response.sources:
                sources_str = ", ".join([str(s) for s in response.sources])
                print(f"Sources: {sources_str}")
            if response.handoff_recommended:
                print("[!] Notice: Human support handoff recommended.")
            print("-" * 60 + "\n")
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting CLI.")
            break


def main():
    parser = argparse.ArgumentParser(description="Aster & Row Reliable RAG Support Agent CLI")
    parser.add_argument("--eval", action="store_true", help="Run the full evaluation suite")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logs")
    args = parser.parse_args()

    if args.eval:
        run_evaluation()
    else:
        interactive_cli(debug=args.debug)


if __name__ == "__main__":
    main()
