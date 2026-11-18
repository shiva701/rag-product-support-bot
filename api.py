"""HTTP API for the support bot. Run with:  uvicorn api:app --reload --port 8000"""

import json
from collections.abc import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from bot import answer, answer_stream
from products import PRODUCTS

app = FastAPI(title="Multi-Product Support API")


class ChatRequest(BaseModel):
    question: str
    product_id: str | None = None  # leave out to let the router agent pick the product
    thread_id: str | None = None  # same id for every turn of one conversation


class TraceStep(BaseModel):
    agent: str
    detail: str


class ChatResponse(BaseModel):
    found: bool
    answer: str
    citations: list[str]
    refused_by: str | None
    source: str | None  # "docs", "general" (model's own knowledge), or null
    product: str | None  # the product whose agent handled the question
    product_name: str | None
    routed_by: str | None  # "user", "router", or "sticky"
    trace: list[TraceStep]  # the agents that ran, in order
    thread_id: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/products")
def products():
    return [p.public() for p in PRODUCTS.values()]


# Plain `def` (not async): answer() blocks on the embedder and Ollama,
# so FastAPI runs it in a worker thread instead of stalling the server.
def _validate(req: ChatRequest) -> str:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is empty.")
    if req.product_id is not None and req.product_id not in PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Unknown product '{req.product_id}'.")
    return question


def _response(r: dict) -> ChatResponse:
    return ChatResponse(**{k: v for k, v in r.items() if k != "hits"})


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    question = _validate(req)
    try:
        r = answer(question, product_id=req.product_id, thread_id=req.thread_id)
    except Exception as e:  # most often: Ollama isn't running
        raise HTTPException(status_code=503, detail=f"Bot unavailable: {e}") from e
    return _response(r)


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    """Same as /api/chat, but streams the agents' progress as it happens.

    The response is newline-delimited JSON, one event per line:
      {"type": "progress", "agent": "router", "status": "running" | "done", "detail": "..."}
      {"type": "answer", ...the same fields as /api/chat...}     (last line on success)
      {"type": "error", "detail": "..."}                         (last line on failure)
    """
    question = _validate(req)

    def events() -> Iterator[str]:
        yield json.dumps(
            {"type": "progress", "agent": "api", "status": "done", "detail": "Question received"}
        ) + "\n"
        try:
            for kind, data in answer_stream(question, req.product_id, req.thread_id):
                if kind == "progress":
                    yield json.dumps({"type": "progress", **data}) + "\n"
                else:
                    yield json.dumps({"type": "answer", **_response(data).model_dump()}) + "\n"
        # The response has already started (status 200), so an error can't become an HTTP error
        # code any more. It's sent as the last event instead. Most often: Ollama isn't running.
        except Exception as e:  # pylint: disable=broad-exception-caught
            yield json.dumps({"type": "error", "detail": f"Bot unavailable: {e}"}) + "\n"

    # A plain generator runs in a worker thread, like the blocking /api/chat handler.
    return StreamingResponse(
        events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache"}
    )
