import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge-base"
DATA_DIR = BASE_DIR / "data"
ORDERS_FILE = DATA_DIR / "orders.json"
EVALUATION_DIR = BASE_DIR / "evaluation"
EVAL_CASES_FILE = EVALUATION_DIR / "visible-cases.json"

# Operational Snapshot Time (from orders.json)
SNAPSHOT_AT = "2026-08-15T12:00:00Z"

# Model Configuration
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
