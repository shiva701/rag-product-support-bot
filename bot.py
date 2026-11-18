"""The one function the rest of the app calls: answer(). The work happens in graph.py."""

import uuid

from graph import run
from products import PRODUCTS, get_product


def answer(question: str, product_id: str | None = None, thread_id: str | None = None) -> dict:
    """Answer one question.

    product_id  send the question straight to that product's agent. Leave it out and the
                router agent picks the product from the question.
    thread_id   pass the same id for every turn of a conversation, so follow-up questions
                stay with the same product. Leave it out for a one-off question.
    """
    if product_id is not None:
        get_product(product_id)  # raises KeyError for an unknown product
    thread_id = thread_id or uuid.uuid4().hex
    state = run(question, product_id, thread_id)

    product = PRODUCTS.get(state.get("product") or "")
    return {
        "found": state["found"],  # True when the bot answered (from docs or general)
        "answer": state["answer"],
        "citations": state["citations"],
        "refused_by": state[
            "refused_by"
        ],  # "router", "retrieval_gate", "model", "model_error", or None
        "source": state["source"],  # "docs", "general", or None when not answered
        "product": product.id if product else None,
        "product_name": product.name if product else None,
        "routed_by": state["routed_by"],  # "user", "router", or "sticky"
        "trace": state["trace"],
        "hits": state["hits"],
        "thread_id": thread_id,
    }
