from pathlib import Path

def load_documents(folder: str) -> list[dict]:
    """Return [{"source": "user_manual.md", "text": "..."}, ...]."""
    docs = []
    for path in sorted(Path(folder).glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            docs.append({"source": path.name, "text": text})
    return docs
