# Session 1 — Anthropic-powered FastAPI Service

A small [FastAPI](https://fastapi.tiangolo.com/) web service that wraps Anthropic's
Claude models to provide a few text endpoints: free-form Q&A (with both a
structured and a streaming variant), text summarization, and sentiment analysis.

It uses the official `anthropic` Python SDK and Claude's native **structured
outputs** (`client.messages.parse()` with Pydantic models), so responses are
validated against typed schemas before they're returned.

The service is containerized with Docker and deploys to [Render](https://render.com).

---

## What it does

| Capability | Endpoint | Output |
|------------|----------|--------|
| Health/root check | `GET /`, `GET /health` | Simple JSON status |
| Ask a question (structured) | `POST /ask` | Validated `Answer` (answer, sources, confidence) |
| Ask a question (streaming) | `POST /ask/stream` | Plain-text token stream |
| Summarize text | `POST /summarize` | Validated `Summary` (summary, key points) |
| Analyze sentiment | `POST /analyze-sentiment` | Validated `SentimentResult` (sentiment, score, reasoning) |

Default model: `claude-sonnet-4-5` (configurable via the `MODEL` constant in `main.py`).

---

## Tech stack

- **Python 3.14** (see `.python-version`)
- **[uv](https://docs.astral.sh/uv/)** for dependency management and running
- **FastAPI** + **Uvicorn** (ASGI server)
- **anthropic** SDK + **Pydantic** for structured outputs
- **Docker** for containerization
- **Render** for hosting

## Project structure

```
session-1/
├── main.py                       # FastAPI application (all endpoints)
├── anthropic_client_requests.py  # Standalone Anthropic wrapper using raw `requests` (learning reference)
├── anthropic_client_sdk.py       # Standalone Anthropic wrapper using the SDK (learning reference)
├── simple_env_test.py            # Minimal ASGI/env sanity-check script
├── Dockerfile                    # Container build (uv-based)
├── .dockerignore
├── pyproject.toml                # Project metadata + dependencies
└── uv.lock                       # Pinned dependency lockfile

render.yaml                       # Render Blueprint (lives at the REPO ROOT, one level up)
```

> Note: `main.py` is the deployed application. The two `anthropic_client_*.py`
> files are standalone learning references and are not imported by the app.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
  (`brew install uv` or the official install script)
- An **Anthropic API key** (`ANTHROPIC_API_KEY`)
- [Docker](https://docs.docker.com/get-docker/) (only needed for the container build)

---

## Setup for development

### 1. Install dependencies

From the `session-1` directory, `uv` creates a virtual environment and installs
the locked dependencies automatically:

```bash
cd session-1
uv sync
```

### 2. Provide your Anthropic API key

The app calls `load_dotenv()` on startup, so the key can live in a `.env` file
(searched in the current directory and parent directories) or be exported in your
shell. Create a `.env` with:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Alternatively, export it directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

> The key is read from the environment at startup; it is never hardcoded or committed.

### 3. Run the development server

`--reload` restarts the server automatically when you edit files:

```bash
uv run uvicorn main:app --reload
```

The server starts on `http://127.0.0.1:8000`. Interactive API docs are available at
`http://127.0.0.1:8000/docs` (Swagger UI) and `http://127.0.0.1:8000/redoc`.

---

## Build and containerize

The `Dockerfile` uses the `uv` toolchain to install from `pyproject.toml` + `uv.lock`
(no `requirements.txt` needed) and binds to `$PORT` at runtime (falling back to `8000`).

### Build the image

```bash
cd session-1
docker build -t session-1 .
```

### Run the container

Pass the API key at runtime — it is **not** baked into the image:

```bash
# Option A: explicit variable
docker run --rm -p 8000:8000 -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" session-1

# Option B: an env file
docker run --rm -p 8000:8000 --env-file .env session-1
```

Then visit `http://localhost:8000/health`.

> If host port `8000` is already in use, map a different host port, e.g.
> `-p 8080:8000` (the container always listens on `8000` internally unless `PORT` is set).

---

## Deploy to Render

Deployment is defined as Infrastructure-as-Code in **`render.yaml`** (at the repo root).
It declares a single Docker-based web service:

```yaml
services:
  - type: web
    name: session-1-api
    runtime: docker
    plan: free
    region: oregon
    branch: main
    dockerfilePath: ./session-1/Dockerfile
    dockerContext: ./session-1
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false
```

### Where the API key resides on Render

`ANTHROPIC_API_KEY` is declared with **`sync: false`**. This means:

- The value is **not** stored in the repository or in `render.yaml`.
- When you create/apply the Blueprint, Render **prompts you to enter the key** in the
  Dashboard. It is then stored as an encrypted **environment variable on the service**
  (Dashboard → your service → **Environment**).
- At runtime Render injects it into the container's environment, where the app reads it
  via `anthropic.Anthropic()`.

### Deploy steps

1. Ensure `render.yaml` is committed and pushed to `main`.
2. Open the Blueprint deeplink:

   ```
   https://dashboard.render.com/blueprint/new?repo=https://github.com/mpuglin/ai-engineering-bootcamp-python
   ```

3. Complete Git OAuth if prompted, then enter the `ANTHROPIC_API_KEY` value when asked.
4. Click **Apply**. Render builds the Docker image and deploys the service.

With `autoDeploy: true`, every push to `main` triggers a new deploy automatically.

> **Free plan note:** the service spins down when idle, so the first request after a
> quiet period may take ~15–50s to cold-start.

---

## API reference

All examples assume a local server at `http://localhost:8000`. To call the deployed
service instead, swap in your Render URL (e.g. `https://session-1-api.onrender.com`).

On any upstream failure (timeout, rate limit, connection, or non-conforming model
output), the JSON endpoints return `{"error": "..."}` instead of the success schema.

### `GET /` and `GET /health`

Lightweight liveness checks.

```bash
curl http://localhost:8000/health
```

```json
{ "status": "health is okay" }
```

### `POST /ask`

Ask a question and get a **structured** answer. Optional `context` is sent as the
system prompt.

**Request body** (`Question`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | yes | The question to ask |
| `context` | string | no | Optional system prompt / context |

**Response** (`Answer`): `answer` (string), `sources` (string array), `confidence` (float).

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the capital of France? Cite one source."}'
```

```json
{
  "answer": "The capital of France is Paris.",
  "sources": ["Encyclopedia Britannica"],
  "confidence": 1.0
}
```

### `POST /ask/stream`

Same input as `/ask`, but streams the answer back as plain text as it is generated.
Use `curl -N` to disable buffering and see tokens arrive incrementally.

**Request body**: same `Question` shape as `/ask`.

**Response**: `text/plain` stream (not JSON).

```bash
curl -N -X POST http://localhost:8000/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "Write a two-sentence story about a robot."}'
```

```
In a quiet workshop, a small robot flickered to life and looked at its hands for
the first time. It decided, then and there, that it would learn to build something
of its own.
```

### `POST /summarize`

Summarize a block of text into a short summary plus key points.

**Request body** (`Document`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | yes | The text to summarize |

**Response** (`Summary`): `summary` (string), `key_points` (string array).

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "The Apollo program ran from 1961 to 1972. Apollo 11 landed the first humans on the Moon in July 1969. Twelve astronauts walked on the Moon across six successful missions."}'
```

```json
{
  "summary": "The Apollo program (1961-1972) achieved the first human Moon landing with Apollo 11 in 1969; twelve astronauts walked on the Moon across six missions.",
  "key_points": [
    "Apollo program operated from 1961 to 1972",
    "Apollo 11 achieved the first human Moon landing in July 1969",
    "Twelve astronauts walked on the Moon",
    "Six successful Moon landing missions"
  ]
}
```

### `POST /analyze-sentiment`

Analyze the sentiment of a block of text.

**Request body** (`Document`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | yes | The text to analyze |

**Response** (`SentimentResult`): `sentiment` (`"positive"` \| `"negative"` \| `"neutral"`),
`score` (float, roughly -1.0 to 1.0), `reasoning` (string).

```bash
curl -X POST http://localhost:8000/analyze-sentiment \
  -H "Content-Type: application/json" \
  -d '{"text": "The product broke after two days and support never replied. Deeply disappointed."}'
```

```json
{
  "sentiment": "negative",
  "score": -0.85,
  "reasoning": "The text reports a product failure and unresponsive support, with the phrase 'deeply disappointed' reinforcing strong negativity."
}
```
