import os
from dotenv import load_dotenv

load_dotenv()

# Fully local setup: sentence-transformers for embeddings, Ollama for chat.
EMBED_MODEL = os.getenv("EMBED_MODEL", "google/embeddinggemma-300m")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemma4")   # any model from `ollama list`

KB_DIR = "kb"
INDEX_DIR = "index"

MAX_SECTION_CHARS = 1200   # split sections longer than this
TOP_K = 4                  # sections passed to the model
MIN_SCORE = 0.30           # refusal gate; calibrate this with calibrate.py

ESCALATION_MESSAGE = (
    "I'm not sure about that one, and I don't want to guess. "
    "Please contact RAG support at support@rag.example "
    "and a specialist will help you."
)
