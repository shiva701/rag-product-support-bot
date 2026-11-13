# Kettlewise K2 Support Bot

A local RAG (retrieval-augmented generation) support bot for the fictional *Kettlewise K2 Smart Kettle*. It answers questions only from the docs in `kb/`, cites its sources, and escalates to a human when the docs don't cover the question.

Everything runs on your machine: no API keys or usage costs.

| Part | Tool |
|---|---|
| Embeddings | Hugging Face model via `sentence-transformers` (default `google/embeddinggemma-300m`) |
| Chat model | Ollama (default `llama3.2`) |
| API | FastAPI on port 8000 |
| Web UI | React + Vite on port 5173 |

---

## 1. Prerequisites

- **Python 3.12+** and **Poetry 2.0+**
- **Node.js 18+** and npm (only for the web UI)
- **Ollama**: install from https://ollama.com
- **Hugging Face account** (only for gated models such as `google/embeddinggemma-300m`)

---

## 2. One-time setup

### Python environment

Dependencies are managed with [Poetry](https://python-poetry.org) (2.0+) and declared in `pyproject.toml`.

```bash
pipx install poetry          # or: brew install poetry
cd product-support-bot
poetry install               # creates ./.venv (see poetry.toml) and installs deps
source .venv/bin/activate    # or prefix commands with `poetry run`
```

Add or remove packages with `poetry add <pkg>` / `poetry remove <pkg>`; commit both `pyproject.toml` and `poetry.lock`.

### Chat model

```bash
ollama pull llama3.2
```

### Hugging Face access (gated embedding model)

`google/embeddinggemma-300m` requires accepting Google's license:

1. Open https://huggingface.co/google/embeddinggemma-300m and accept the terms.
2. Create a **Read** token at https://huggingface.co/settings/tokens.
3. Log in once:

   ```bash
   hf auth login        # older versions: huggingface-cli login
   ```

   Or add `HF_TOKEN=hf_...` to `.env`.

The model downloads on first use and is cached in `~/.cache/huggingface/`. After that it runs locally.

> To skip this step, use a non-gated model such as `BAAI/bge-small-en-v1.5` or `all-MiniLM-L6-v2` (see [Changing models](#7-changing-models)).

### Environment file

Create `.env` in the project root:

```dotenv
EMBED_MODEL=google/embeddinggemma-300m
CHAT_MODEL=llama3.2
# HF_TOKEN=hf_...   # only if you didn't use `hf auth login`
```

Never commit `.env` or share your token.

### Web UI dependencies

```bash
cd frontend
npm install
cd ..
```

---

## 3. Build the index

Run this the first time, and again whenever you edit files in `kb/` or change `EMBED_MODEL`:

```bash
source .venv/bin/activate
python ingest.py
```

This splits the docs into sections, embeds them, and saves the index to `index/`.

---

## 4. Run the application

**Ollama must be running.** Open the Ollama app, or run `ollama serve` in a terminal. Check it with:

```bash
curl localhost:11434        # should print "Ollama is running"
```

### Option A: Web UI

Use two terminals.

```bash
# Terminal 1: API (project root)
source .venv/bin/activate
uvicorn api:app --reload --port 8000
```

```bash
# Terminal 2: UI
cd frontend
npm run dev
```

Open **http://localhost:5173**.

### Option B: Terminal chat

```bash
source .venv/bin/activate
python chat.py
```

Type `debug` to toggle retrieval scores, `quit` to exit.

### Stop the servers

If a server is running in your terminal, press **Ctrl+C** in that terminal.

If it's running in the background, or you're not sure where it is, stop both servers by port:

```bash
lsof -ti tcp:8000 | xargs kill    # API (uvicorn)
lsof -ti tcp:5173 | xargs kill    # UI (Vite)
```

Or by name:

```bash
pkill -f "uvicorn api:app"        # API
pkill -f vite                     # UI (stops every Vite server, including other projects)
```

Check that both are stopped (no output means nothing is listening):

```bash
lsof -i tcp:8000 -i tcp:5173
```

If a server won't stop, force it with `kill -9`, e.g. `lsof -ti tcp:8000 | xargs kill -9`.

If you started the API from the VS Code debugger, stop it with the red stop button or **⇧F5**.

Ollama keeps running separately. Quit it from the menu bar icon or with `pkill ollama` if you want to free its memory.

---

## 5. API

**Ask a question**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "My kettle shows E1, what do I do?"}'
```

Response:

```json
{
  "found": true,
  "answer": "Add at least 0.5 liters of water and press START.",
  "citations": ["troubleshooting.md#Error Code E1"],
  "refused_by": null
}
```

When the bot refuses, `found` is `false` and `refused_by` is `"retrieval_gate"` or `"model"`.

**Health check**

```bash
curl http://localhost:8000/api/health
```

Interactive docs: **http://localhost:8000/docs**. To use the curl in Postman, choose **Import** and paste it.

---

## 6. Tune and evaluate

```bash
source .venv/bin/activate

python calibrate.py     # suggests a MIN_SCORE refusal threshold
python evaluate.py      # grades the bot against eval_set.json
```

`evaluate.py` reports three scores:

| Score | Measures |
|---|---|
| Answer/refuse decision | Answered real questions, refused out-of-scope ones |
| Retrieval hit rate | The right doc section was found |
| Answer content correct | The answer contains the key facts |

Set `MIN_SCORE` in `config.py` from the calibration output. If answerable and unanswerable scores overlap, lean low and let the model handle borderline questions.

---

## 7. Changing models

### Chat model

Any model from `ollama list` works:

```bash
ollama pull gemma4
```

Set `CHAT_MODEL=gemma4` in `.env`, then restart the API. No re-indexing needed.

### Embedding model

`embedding.py` uses `sentence-transformers`, which loads **Hugging Face** models only (not Ollama models).

1. Set `EMBED_MODEL` in `.env`, e.g. `BAAI/bge-small-en-v1.5`.
2. Rebuild and re-tune:

   ```bash
   rm -rf index/
   python ingest.py
   python calibrate.py     # update MIN_SCORE in config.py
   python evaluate.py
   ```

3. Restart the API.

> Always search with the same embedding model you indexed with. Changing it without re-running `ingest.py` breaks retrieval.

---

## 8. Project structure

```
product-support-bot/
├── .env              # model settings (not committed)
├── config.py         # settings: models, TOP_K, MIN_SCORE, escalation message
├── loader.py         # reads kb/*.md
├── chunker.py        # splits docs into one chunk per section
├── embedding.py      # text -> vectors (sentence-transformers)
├── vector_store.py   # saves, loads, and searches the index
├── ingest.py         # builds index/
├── bot.py            # retrieve -> refusal gates -> Ollama -> JSON answer
├── api.py            # FastAPI server
├── chat.py           # terminal chat
├── calibrate.py      # threshold helper
├── evaluate.py       # eval runner
├── eval_set.json     # test questions
├── kb/               # knowledge base docs
├── index/            # generated by ingest.py
└── frontend/         # React UI
```

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `Connection refused` on port 11434, or API returns 503 | Start Ollama (`ollama serve` or the app) |
| `model "llama3.2" not found` | `ollama pull llama3.2` |
| `401 Unauthorized` from huggingface.co | Accept the model license and log in (see setup) |
| `FileNotFoundError: index/vectors.npy` | Run `python ingest.py` |
| Shape mismatch or nonsense scores after a model change | `rm -rf index/` then `python ingest.py` |
| Bot refuses questions the docs answer | Lower `MIN_SCORE`, or try a stronger embedding model |
| Right section found but answer says "not sure" | Try a bigger chat model, e.g. `CHAT_MODEL=gemma4` |
| First answer is slow | Ollama is loading the model; later answers are faster |
| UI says "Couldn't reach the support bot" | Start the API on port 8000 |
