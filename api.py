"""HTTP API for the support bot. Run with:  uvicorn api:app --reload --port 8000"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from bot import answer

app = FastAPI(title="Kettlewise K2 Support API")


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    found: bool
    answer: str
    citations: list[str]
    refused_by: str | None


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Plain `def` (not async): answer() blocks on the embedder and Ollama,
# so FastAPI runs it in a worker thread instead of stalling the server.
@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is empty.")
    try:
        r = answer(question)
    except Exception as e:  # most often: Ollama isn't running
        raise HTTPException(status_code=503, detail=f"Bot unavailable: {e}")
    return ChatResponse(found=r["found"], answer=r["answer"],
                        citations=r["citations"], refused_by=r["refused_by"])
