import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "knowledge")
DB_PATH = os.path.join(KNOWLEDGE_DIR, "legion.db")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "5.0"))

Path(KNOWLEDGE_DIR).mkdir(parents=True, exist_ok=True)
