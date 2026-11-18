"""The multi-agent graph (LangGraph).

    START -> router -> <product>_agent -> END                      answered from the docs
                |            |
                |            +-> general_agent -> END              docs had no answer, product allows
                |            |         |                           general knowledge (adds a notice)
                |            +---------+-> escalate -> END         hand over to a human
                +-> clarify -> END                                 no product matched

One <product>_agent node is created for every folder in kb/, so adding a product adds an agent.
Print the diagram with:  python graph.py
"""

from collections.abc import Iterator
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from products import PRODUCTS, Product
from rag import general_answer, grounded_answer, pick_product, retrieve


class State(TypedDict, total=False):
    # Set by the caller on every turn
    question: str
    requested_product: str | None  # set when the user picked a product themselves
    # Remembered between turns of the same thread (the caller never resets it)
    product: str | None  # the product this conversation is about
    # Filled in by the agents on every turn
    routed_by: str | None  # "user", "router", or "sticky"
    hits: list[dict]
    found: bool
    answer: str
    citations: list[str]
    refused_by: str | None  # "router", "retrieval_gate", "model", or "model_error"
    source: str | None  # "docs" or "general"
    trace: list[dict]  # which agents ran, for the UI and debugging


def progress(agent: str, detail: str, status: str = "running") -> None:
    """Report live activity to stream() callers (the web UI). A no-op when not streaming."""
    get_stream_writer()({"agent": agent, "status": status, "detail": detail})


def step(state: State, agent: str, detail: str) -> list[dict]:
    """Record a finished step in the trace and report it as done."""
    progress(agent, detail, status="done")
    return state.get("trace", []) + [{"agent": agent, "detail": detail}]


# --- Router agent ------------------------------------------------------------
def router(state: State) -> dict:
    requested, active = state.get("requested_product"), state.get("product")
    progress("router", "Reading the question to pick a product")
    if requested:
        product, how, detail = requested, "user", "you selected this product"
    elif len(PRODUCTS) == 1:
        product, how, detail = next(iter(PRODUCTS)), "router", "only one product"
    else:
        product = pick_product(state["question"], active)
        how, detail = "router", "chosen from the question"
        if product is None and active:
            # No clear match mid-conversation: stay with the current product and let its
            # agent decide whether it can answer.
            product, how, detail = active, "sticky", "no clear match, kept the current product"
    if product is None:
        return {
            "product": None,
            "routed_by": "router",
            "trace": step(state, "router", "no product matched"),
        }
    return {
        "product": product,
        "routed_by": how,
        "trace": step(state, "router", f"{PRODUCTS[product].name}: {detail}"),
    }


def after_router(state: State) -> str:
    return f"{state['product']}_agent" if state.get("product") else "clarify"


def clarify(state: State) -> dict:
    progress("clarify", "No product matched, asking which one you mean")
    names = ", ".join(p.name for p in PRODUCTS.values())
    return {
        "found": False,
        "refused_by": "router",
        "citations": [],
        "source": None,
        "answer": f"I can help with: {names}. Please mention which one your question "
        "is about, or pick it from the list.",
        "trace": step(state, "clarify", "asked which product"),
    }


# --- Product agents (one per product, all built by this factory) --------------
def make_product_agent(product: Product):
    name = f"{product.id}_agent"

    def agent(state: State) -> dict:
        progress(name, f"Searching the {product.name} documents")
        hits = retrieve(state["question"], product)
        best = hits[0]["score"] if hits else 0.0

        # Gate 1: retrieval. Nothing close enough -> don't even ask the model.
        if best < product.min_score:
            return {
                "hits": hits,
                "found": False,
                "refused_by": "retrieval_gate",
                "trace": step(
                    state, name, f"best match {best:.2f} is below {product.min_score:.2f}"
                ),
            }

        # Gate 2: the model read the sections and says they don't answer it.
        progress(name, f"Found {len(hits)} matching sections, writing the answer")
        result = grounded_answer(state["question"], hits, product)
        if result["error"]:
            # The model's reply was unusable. We don't know whether the documents cover the
            # question, so this goes to a human, never to the general-knowledge agent.
            return {
                "hits": hits,
                "found": False,
                "refused_by": "model_error",
                "trace": step(state, name, "the model's reply was unusable"),
            }
        if not result["answered"]:
            return {
                "hits": hits,
                "found": False,
                "refused_by": "model",
                "trace": step(state, name, "the documents don't answer this"),
            }

        return {
            "hits": hits,
            "found": True,
            "refused_by": None,
            "source": "docs",
            "answer": result["answer"],
            "citations": result["citations"],
            "trace": step(state, name, "answered from the documents"),
        }

    return name, agent


def after_product_agent(state: State) -> str:
    if state.get("found"):
        return END
    if state.get("refused_by") == "model_error":
        return "escalate"
    return "general_agent" if PRODUCTS[state["product"]].general_fallback else "escalate"


# --- General-knowledge agent (only for products with general_fallback = true) -
def general_agent(state: State) -> dict:
    product = PRODUCTS[state["product"]]
    progress("general_agent", "The documents don't cover this, trying general knowledge")
    result = general_answer(state["question"], product)
    if not result["relevant"]:
        return {
            "trace": step(state, "general_agent", f"not a question about {product.general_topic}")
        }
    # The notice is added here in code, not by the model, so it can never be left out.
    return {
        "found": True,
        "refused_by": None,
        "source": "general",
        "citations": [],
        "answer": f"{product.general_notice}\n\n{result['answer']}",
        "trace": step(state, "general_agent", "answered from general knowledge"),
    }


def after_general_agent(state: State) -> str:
    return END if state.get("found") else "escalate"


# --- Escalation --------------------------------------------------------------
def escalate(state: State) -> dict:
    product = PRODUCTS[state["product"]]
    return {
        "found": False,
        "answer": product.escalation_message,
        "citations": [],
        "source": None,
        "trace": step(state, "escalate", "handed over to a human"),
    }


# --- Wiring ------------------------------------------------------------------
def build_graph():
    g = StateGraph(State)
    g.add_node("router", router)
    g.add_node("clarify", clarify)
    g.add_node("general_agent", general_agent)
    g.add_node("escalate", escalate)

    agent_names = []
    for product in PRODUCTS.values():
        name, agent = make_product_agent(product)
        g.add_node(name, agent)
        targets = (
            [END, "general_agent", "escalate"] if product.general_fallback else [END, "escalate"]
        )
        g.add_conditional_edges(name, after_product_agent, targets)
        agent_names.append(name)

    g.add_edge(START, "router")
    g.add_conditional_edges("router", after_router, agent_names + ["clarify"])
    g.add_conditional_edges("general_agent", after_general_agent, [END, "escalate"])
    g.add_edge("escalate", END)
    g.add_edge("clarify", END)

    # The checkpointer remembers each thread's state (here: the active product) between turns.
    # InMemorySaver forgets everything on restart; swap in SqliteSaver to keep it.
    return g.compile(checkpointer=InMemorySaver())


app = build_graph()


def _turn(question: str, product_id: str | None) -> dict:
    """Input for one turn. Per-turn fields are reset here; 'product' carries over in a thread."""
    return {
        "question": question,
        "requested_product": product_id,
        "routed_by": None,
        "hits": [],
        "found": False,
        "answer": "",
        "citations": [],
        "refused_by": None,
        "source": None,
        "trace": [],
    }


def run(question: str, product_id: str | None, thread_id: str) -> State:
    """Run one turn and return the final state."""
    config = {"configurable": {"thread_id": thread_id}}
    return app.invoke(_turn(question, product_id), config=config)


def stream(question: str, product_id: str | None, thread_id: str) -> Iterator[tuple[str, dict]]:
    """Run one turn, yielding ("progress", event) as the agents work, then ("final", state)."""
    config = {"configurable": {"thread_id": thread_id}}
    state: State = {}
    for mode, chunk in app.stream(
        _turn(question, product_id), config=config, stream_mode=["custom", "values"]
    ):
        if mode == "custom":
            yield "progress", chunk
        else:
            state = chunk  # the full state after each step; the last one is the result
    yield "final", state


if __name__ == "__main__":
    print(app.get_graph().draw_mermaid())
