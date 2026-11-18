"""HTTP API for the support bot. Run with:  uvicorn api:app --reload --port 8000"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from bot import answer
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
@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is empty.")
    if req.product_id is not None and req.product_id not in PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Unknown product '{req.product_id}'.")
    try:
        r = answer(question, product_id=req.product_id, thread_id=req.thread_id)
    except Exception as e:  # most often: Ollama isn't running
        raise HTTPException(status_code=503, detail=f"Bot unavailable: {e}") from e
    return ChatResponse(**{k: v for k, v in r.items() if k != "hits"})
