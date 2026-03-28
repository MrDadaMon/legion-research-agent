import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "knowledge")
DB_PATH = os.path.join(KNOWLEDGE_DIR, "legion.db")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "5.0"))
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", os.path.join(KNOWLEDGE_DIR, "vault"))
USE_OBSIDIAN_VAULT = os.getenv("USE_OBSIDIAN_VAULT", "true").lower() == "true"

Path(KNOWLEDGE_DIR).mkdir(parents=True, exist_ok=True)
