from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[0]  # = medi_agent/

ACCOUNTS_PATH = Path(os.getenv("ACCOUNTS_PATH", str(PROJECT_ROOT / "data" / "vezeeta_accounts.json")))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(PROJECT_ROOT / "data" / "vezeeta_alexandria_autorec.sqlite")))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")