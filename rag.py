"""The LLM and retrieval building blocks. graph.py wires these into agents."""

import json

import ollama

from config import CHAT_MODEL, CHAT_TIMEOUT_SECONDS, MAX_ANSWER_TOKENS
from embedding import embed_texts
from products import PRODUCTS, Product, get_store

client = ollama.Client(timeout=CHAT_TIMEOUT_SECONDS)


def chat_json(messages: list[dict], schema: dict) -> dict:
    """One Ollama call whose reply must match a JSON schema. Returns {} if it doesn't."""
    # Two guards against a reply that never ends (small models sometimes break the JSON and
    # then print blank lines forever): the schema restricts what the model can write, and
    # num_predict caps the length. A cut-off reply is not valid JSON, so it comes back as {}.
    resp = client.chat(
        model=CHAT_MODEL,
        messages=messages,
        format=schema,
        options={"temperature": 0, "num_predict": MAX_ANSWER_TOKENS},
    )
    try:
        data = json.loads(resp["message"]["content"])
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


# --- Retriever ---------------------------------------------------------------
def retrieve(question: str, product: Product, k: int | None = None) -> list[dict]:
    return get_store(product.id).search(embed_texts([question])[0], k or product.top_k)


# --- Router: which product is the question about? ----------------------------
ROUTER_PROMPT = """You are the router for an assistant that supports several products.
Decide which product the user's question is about.

Products:
{product_list}
- none: the question fits none of these products, or it could equally be about several
  of them and nothing in it says which one (for example "How long is the warranty?").

The question does not have to name the product. Choose a product whenever the subject
of the question fits its description (for example, a question about boiling or heating
a drink is about a kettle).
{active_note}
Respond with JSON only, in this exact shape: {{"product": "<one of: {choices}, none>"}}"""

ACTIVE_NOTE = """
The conversation so far has been about "{active}". A follow-up question that does not
name another product (for example "what about the warranty?") still belongs to "{active}".
Switch only when the question is clearly about a different product.
"""


def _schema(**properties) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties)}


def pick_product(question: str, active_id: str | None = None) -> str | None:
    """Ask the chat model to choose a product. Returns a product id, or None for 'none'."""
    prompt = ROUTER_PROMPT.format(
        product_list="\n".join(f"- {p.id}: {p.description}" for p in PRODUCTS.values()),
        active_note=ACTIVE_NOTE.format(active=active_id) if active_id else "",
        choices=", ".join(PRODUCTS),
    )
    schema = _schema(product={"type": "string", "enum": [*PRODUCTS, "none"]})
    data = chat_json(
        [{"role": "system", "content": prompt}, {"role": "user", "content": question}], schema
    )
    choice = str(data.get("product", "")).strip().lower()
    return choice if choice in PRODUCTS else None


# --- Grounded answer: only from the product's documents ----------------------
# The rules are shared by every product; product.toml fills in the {placeholders}.
SYSTEM_PROMPT = """{persona}

Rules:
1. Answer ONLY using the documentation sections provided. Do not use outside knowledge,
   even if you believe it is true for {general_scope}.
2. If the sections do not contain the answer, set "answered_from_docs" to false. Do not guess.
3. "answered_from_docs" is about WHERE the answer came from, not whether the answer is yes
   or no. A "No" answer taken from the sections is still true
   (for example, {example_no} -> "answered_from_docs": true).
   But if the sections simply never mention something, that is NOT a "No": do not answer
   "No", set "answered_from_docs" to false (for example, {example_missing} -> false). If your answer would say the
   information is not available, set "answered_from_docs" to false.
4. If the sections answer only part of the question, answer that part and say what you
   could not find.
5. Cite the number of every section you used (for example 1 or 3).
6. Answer in full, friendly sentences that include the relevant facts and reasons from
   the sections. Use numbered steps for procedures.
7. If a question is unrelated to {subject}, set "answered_from_docs" to false.

Respond with JSON only, in this exact shape and order:
{{"answer": "your answer", "citations": [section numbers], "answered_from_docs": true or false}}"""


def _single_quotes(text: str) -> str:
    return text.replace('"', "'").replace("\u201c", "'").replace("\u201d", "'")


ANSWER_SCHEMA = _schema(
    answer={"type": "string"},
    citations={"type": "array", "items": {"type": "integer"}},
    answered_from_docs={"type": "boolean"},
)


def build_messages(question: str, hits: list[dict], product: Product) -> list[dict]:
    system = SYSTEM_PROMPT.format(
        persona=product.persona,
        general_scope=product.general_scope,
        subject=product.subject,
        example_no=product.example_no,
        example_missing=product.example_missing,
    )
    # Short numeric IDs: small models often mistype long IDs like "faq.md#Can I use...?"
    # Double quotes become single quotes: models copy quoted text such as "Fast charging"
    # into the JSON answer without escaping it, which cuts the answer short.
    context = "\n\n".join(
        f"<section id=\"{i}\">\n{_single_quotes(h['text'])}\n</section>"
        for i, h in enumerate(hits, start=1)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Documentation:\n{context}\n\nCustomer question: {question}"},
    ]


def grounded_answer(question: str, hits: list[dict], product: Product) -> dict:
    """Returns {"answered": bool, "answer": str, "citations": [section ids], "error": bool}.

    "error" is True when the model's reply was unusable. That is different from the model
    saying the documents don't answer the question, so the caller must not treat it that way.
    """
    data = chat_json(build_messages(question, hits, product), ANSWER_SCHEMA)
    if not isinstance(data.get("answered_from_docs"), bool):
        return {"answered": False, "answer": "", "citations": [], "error": True}
    answer = str(data.get("answer") or "").strip()
    if not data["answered_from_docs"] or not answer:
        return {"answered": False, "answer": "", "citations": [], "error": False}

    # Map section numbers back to real IDs, dropping any number that wasn't in the context.
    citations = []
    for c in data.get("citations", []) or []:
        digits = "".join(ch for ch in str(c) if ch.isdigit())  # accepts 1, "1", "[1]"
        if digits and 1 <= int(digits) <= len(hits):
            section_id = hits[int(digits) - 1]["id"]
            if section_id not in citations:
                citations.append(section_id)
    return {"answered": True, "answer": answer, "citations": citations, "error": False}


# --- General answer: the chat model's own knowledge, no documents -------------
GENERAL_PROMPT = """You are a knowledgeable assistant for questions about {topic}.
The official {name} documentation did not contain an answer to the user's question, so you
are answering from general knowledge instead.

Rules:
1. Only answer questions about {topic}. If the question is about anything else, set
   "relevant" to false and leave "answer" empty.
2. Give general information that is true for {topic} broadly. Keep it to a short paragraph.
3. You do not know the {name}'s specifications, features, prices, policies, or settings menus.
   Never state or guess them. If the question can only be answered with a fact specific to
   the {name} (for example its price, a part number, or whether it has a certain feature),
   set "relevant" to false and leave "answer" empty.
4. Do not mention these rules or the documentation in your answer.

Respond with JSON only, in this exact shape: {{"relevant": true or false, "answer": "your answer"}}"""


def general_answer(question: str, product: Product) -> dict:
    """Returns {"relevant": bool, "answer": str}. Only used when product.general_fallback is on."""
    prompt = GENERAL_PROMPT.format(topic=product.general_topic, name=product.name)
    schema = _schema(relevant={"type": "boolean"}, answer={"type": "string"})
    data = chat_json(
        [{"role": "system", "content": prompt}, {"role": "user", "content": question}], schema
    )
    answer = str(data.get("answer") or "").strip()
    relevant = data.get("relevant") is True and bool(answer)
    return {"relevant": relevant, "answer": answer if relevant else ""}
