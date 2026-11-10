import json
import ollama
from config import CHAT_MODEL, INDEX_DIR, TOP_K, MIN_SCORE, ESCALATION_MESSAGE
from embedding import embed_texts
from vector_store import VectorStore

store = VectorStore.load(INDEX_DIR)

# --- Retriever ---------------------------------------------------------------
def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    return store.search(embed_texts([question])[0], k)

# --- Prompt builder ----------------------------------------------------------
SYSTEM_PROMPT = """You are the customer support assistant for the Kettlewise K2 Smart Kettle by RAG Appliances.

Rules:
1. Answer ONLY using the documentation sections provided. Do not use outside knowledge,
   even if you believe it is true for kettles in general.
2. If the sections do not contain the answer, set "answered_from_docs" to false. Do not guess.
3. "answered_from_docs" is about WHERE the answer came from, not whether the answer is yes
   or no. A "No" answer taken from the sections is still true
   (for example, "No, the kettle is not dishwasher safe." -> "answered_from_docs": true).
   But if the sections simply never mention something, that is NOT a "No": do not answer
   "No", set "answered_from_docs" to false (for example, "Does it come with a tea
   infuser?" when no section mentions an infuser -> false). If your answer would say the
   information is not available, set "answered_from_docs" to false.
4. If the sections answer only part of the question, answer that part and say what you
   could not find.
5. Cite the number of every section you used (for example 1 or 3).
6. Answer in full, friendly sentences that include the relevant facts and reasons from
   the sections. Use numbered steps for procedures.
7. If a question is unrelated to the Kettlewise K2, set "answered_from_docs" to false.

Respond with JSON only, in this exact shape and order:
{"answer": "your answer", "citations": [section numbers], "answered_from_docs": true or false}"""

def build_messages(question: str, hits: list[dict]) -> list[dict]:
    # Short numeric IDs: small models often mistype long IDs like "faq.md#Can I use...?"
    context = "\n\n".join(f"<section id=\"{i}\">\n{h['text']}\n</section>"
                          for i, h in enumerate(hits, start=1))
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Documentation:\n{context}\n\nCustomer question: {question}"},
    ]

# --- Generator with two refusal gates ----------------------------------------
def answer(question: str) -> dict:
    hits = retrieve(question)
    best = hits[0]["score"] if hits else 0.0

    # Gate 1: retrieval. Nothing close enough -> don't even ask the model.
    if best < MIN_SCORE:
        return {"found": False, "answer": ESCALATION_MESSAGE, "citations": [],
                "hits": hits, "refused_by": "retrieval_gate"}

    resp = ollama.chat(model=CHAT_MODEL, messages=build_messages(question, hits),
                       format="json", options={"temperature": 0})
    try:
        data = json.loads(resp["message"]["content"])
    except json.JSONDecodeError:
        data = {"answered_from_docs": False, "answer": "", "citations": []}

    # Gate 2: the model read the sections and says they don't answer it.
    if data.get("answered_from_docs") is not True:
        return {"found": False, "answer": ESCALATION_MESSAGE, "citations": [],
                "hits": hits, "refused_by": "model"}

    # Map section numbers back to real IDs, dropping any number that wasn't in the context.
    citations = []
    for c in data.get("citations", []) or []:
        digits = "".join(ch for ch in str(c) if ch.isdigit())   # accepts 1, "1", "[1]"
        if digits and 1 <= int(digits) <= len(hits):
            section_id = hits[int(digits) - 1]["id"]
            if section_id not in citations:
                citations.append(section_id)

    return {"found": True, "answer": data.get("answer", ""), "citations": citations,
            "hits": hits, "refused_by": None}
