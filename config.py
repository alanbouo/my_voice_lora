"""Configuration for the RAG writing assistant."""
import logging
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"
EXAMPLES_DIR = DATA_DIR / "examples"
GOLDEN_EXAMPLES_FILE = DATA_DIR / "golden_examples.json"
FEEDBACK_LOG_FILE = DATA_DIR / "feedback_log.json"
LOG_FILE = DATA_DIR / "app.log"

# Embedding model (runs locally via sentence-transformers)
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # 384 dims, fast, good quality

# LLM settings (via Ollama)
LLM_MODEL = "qwen2.5:7b"
LLM_BASE_URL = "http://localhost:11434"

# RAG settings
NUM_EXAMPLES_TO_RETRIEVE = 5
MAX_CONTEXT_LENGTH = 4096

# Context categories
CONTEXT_CATEGORIES = [
    "email_professional",
    "linkedin_post",
    "slack_casual",
    "whatsapp_personal",
    "twitter_post",
]

# Tone tags
TONE_TAGS = ["formal", "casual", "friendly", "professional", "witty"]

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)
EXAMPLES_DIR.mkdir(exist_ok=True)

_log_configured = False


def get_logger(name: str) -> logging.Logger:
    global _log_configured
    if not _log_configured:
        _log_configured = True
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
        root.addHandler(fh)
    return logging.getLogger(name)
