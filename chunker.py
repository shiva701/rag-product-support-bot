import re

def split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (doc_title, [(section_title, section_body), ...]) from markdown."""
    title_match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
    doc_title = title_match.group(1).strip() if title_match else "Untitled"

    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    # parts = [preamble, title1, body1, title2, body2, ...]
    sections = []
    for i in range(1, len(parts), 2):
        sec_title = parts[i].strip()
        body = parts[i + 1].strip()
        if body:
            sections.append((sec_title, body))
    return doc_title, sections


def split_long(body: str, max_chars: int) -> list[str]:
    """Split an over-long section on paragraph breaks."""
    if len(body) <= max_chars:
        return [body]
    pieces, current = [], ""
    for para in body.split("\n\n"):
        if current and len(current) + len(para) > max_chars:
            pieces.append(current.strip())
            current = ""
        current += para + "\n\n"
    if current.strip():
        pieces.append(current.strip())
    return pieces


def chunk_documents(docs: list[dict], max_chars: int) -> list[dict]:
    chunks = []
    for doc in docs:
        doc_title, sections = split_sections(doc["text"])
        for sec_title, body in sections:
            for j, piece in enumerate(split_long(body, max_chars)):
                chunks.append({
                    "id": f"{doc['source']}#{sec_title}" + (f"-{j}" if j else ""),
                    "source": doc["source"],
                    "section": sec_title,
                    # Prepend titles so the embedding knows the context.
                    "text": f"{doc_title} > {sec_title}\n{piece}",
                })
    return chunks
