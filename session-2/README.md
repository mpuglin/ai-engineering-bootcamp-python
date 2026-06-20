# Session 2 — Municipal Regulations RAG

A progressive series of Jupyter notebooks that build a **Retrieval-Augmented
Generation (RAG)** system for querying **Baldwin Borough** and **Allegheny
County** municipal regulation PDFs. The final deliverable is a **Gradio web
UI** backed by **contextual embeddings** stored in a persistent **ChromaDB**
index.

This README explains every file in this directory, how the pipeline evolved
across eight notebook iterations, and **step-by-step instructions for
testing the final application** (`ragexperiment-8-gradio-ui.ipynb`).

---

## Table of contents

1. [Quick start (final app only)](#quick-start-final-app-only)
2. [What this project does](#what-this-project-does)
3. [Directory layout](#directory-layout)
4. [Notebook evolution (iterations 1–8)](#notebook-evolution-iterations-18)
5. [Architecture overview](#architecture-overview)
6. [Environment setup](#environment-setup)
7. [Building the vector index (one-time)](#building-the-vector-index-one-time)
8. [When to run what](#when-to-run-what)
9. [Testing the Gradio UI (iteration 8)](#testing-the-gradio-ui-iteration-8)
10. [Troubleshooting](#troubleshooting)
11. [Design decisions and trade-offs](#design-decisions-and-trade-offs)

---

## Quick start (final app only)

If the Chroma index already exists on your machine (or you are setting up
from scratch — see [Building the vector index](#building-the-vector-index-one-time)):

```bash
cd session-2
uv sync
```

Create a `.env` file in the **repository root** (`maven-classes/.env`) with
at least:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
RAG_TOKEN_BUDGET=50000
RAG_TIMEOUT_SECS=30
RAG_LOG_FILE=rag_session_log.csv
```

Start Jupyter, open `ragexperiment-8-gradio-ui.ipynb`, select the `.venv`
kernel, then run cells **1 → 2 → 3 → 6** (skip cell 4 if the index is already
built). Cell 6 launches Gradio at a local URL (typically
`http://127.0.0.1:7860`).

For full testing instructions, see
[Testing the Gradio UI](#testing-the-gradio-ui-iteration-8).

---

## What this project does

| Stage | What happens |
|-------|----------------|
| **Ingest** | Load 32 PDFs from `data/`, split into ~2,823 chunks |
| **Contextualize** (optional but recommended) | Claude (Haiku) writes a short situating description for each chunk using the full source PDF; prompt caching reduces cost |
| **Embed** | OpenAI `text-embedding-3-small` embeds `context + chunk` (or raw chunk for baseline) |
| **Store** | Vectors + metadata persisted in ChromaDB under `data/chroma_store/` |
| **Query** | User question → embed → top-k similarity search → Claude (Sonnet) answers with inline citations |

**Corpus:**

- `data/baldwin/` — 3 Baldwin Borough PDFs
- `data/alleghenycounty/` — 29 Allegheny County regulation PDFs

---

## Directory layout

```
session-2/
├── README.md                          ← this file
├── pyproject.toml                     ← Python dependencies (uv/pip)
├── uv.lock                            ← locked dependency versions
│
├── ragexperiment-1.ipynb              ← iteration 1: chunking basics
├── ragexperiment-2-embedding-eval.ipynb
├── ragexperiment-3-langchain-load.ipynb
├── ragexperiment-4-productionready.ipynb
├── ragexperiment-5-production-simplification.ipynb
├── ragexperiment-6-simplified.ipynb
├── ragexperiment-7-class-architecture.ipynb   ← class-based pipeline + contextual ingest
├── ragexperiment-8-gradio-ui.ipynb            ← FINAL: Gradio web UI ★
│
├── scripts/
│   ├── baseline_ingest.py             ← headless baseline index build (~20 sec)
│   └── contextual_ingest.py           ← headless contextual index build (~2+ hrs)
│
├── data/
│   ├── baldwin/                       ← Baldwin Borough PDFs (3 files)
│   ├── alleghenycounty/               ← Allegheny County PDFs (29 files)
│   ├── test_queries.txt               ← sample questions for manual testing
│   └── chroma_store/                  ← local ChromaDB (gitignored, created at runtime)
│
└── rag_session_log.csv                ← query log from chat sessions (gitignored)
```

**Not in git (created locally):**

| Path | Purpose |
|------|---------|
| `data/chroma_store/` | Persistent vector index |
| `rag_session_log.csv` | CSV log of queries, answers, retrieved chunks |
| `.venv/` | Virtual environment |

---

## Notebook evolution (iterations 1–8)

These notebooks are **historical iterations**. You do not need to run earlier
versions unless you are studying the progression. **Iteration 8 is the final
deliverable.**

| File | Focus | Notes |
|------|-------|-------|
| `ragexperiment-1.ipynb` | Chunking and embedding basics | Early experiments |
| `ragexperiment-2-embedding-eval.ipynb` | Compare embedding models | Evaluation across models |
| `ragexperiment-3-langchain-load.ipynb` | LangChain PDF loading | PyPDFLoader + text splitter |
| `ragexperiment-4-productionready.ipynb` | Production RAG patterns | Multi-model, governance, logging |
| `ragexperiment-5-production-simplification.ipynb` | Simplified production variant | Iteration on #4 |
| `ragexperiment-6-simplified.ipynb` | OpenAI-only embeddings | Baldwin-only corpus; `EphemeralClient` (in-memory, not persisted) |
| `ragexperiment-7-class-architecture.ipynb` | **Class-based architecture** | `VectorDB` + `ContextualVectorDB`; Chroma `PersistentClient`; terminal chat |
| `ragexperiment-8-gradio-ui.ipynb` | **Gradio web UI** ★ | Same classes as #7; browser chat instead of `input()` |

### Iteration 7 — core classes (reference)

Iteration 7 introduces two classes in cell 3:

- **`VectorDB`** — baseline pipeline: PDF → chunk → OpenAI embed → ChromaDB
- **`ContextualVectorDB(VectorDB)`** — extends baseline:
  - `_situate_context()` calls Claude with full PDF + chunk (prompt caching)
  - Embeds `context + chunk`; stores `original_content` in metadata for citations
  - `load_data()` is incremental (skips PDFs already indexed)
  - Auto-resets collection if it finds baseline-only data (no `contextualized_content`)

Iteration 8 copies these classes unchanged and adds a Gradio front end.

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│  INGEST (once, slow — iteration 7 cell 4 or scripts/)           │
│                                                                 │
│  PDF ──► chunk ──► Claude situates chunk ──► embed(context+chunk)│
│                         ▲                      │              │
│                         │ prompt cache           ▼              │
│                    full PDF text              ChromaDB          │
│                    (ephemeral cache)     data/chroma_store/     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  QUERY (every question — iteration 8 cell 6)                    │
│                                                                 │
│  user question ──► embed query ──► Chroma search (top 7)        │
│                         │                                       │
│                         ▼                                       │
│              Claude Sonnet + retrieved passages                 │
│                         │                                       │
│                         ▼                                       │
│              Gradio chat UI + sources panel + CSV log           │
└─────────────────────────────────────────────────────────────────┘
```

### ChromaDB collections

| Collection name | Contents | When built |
|-----------------|----------|------------|
| `regulations_openai_baseline` | Raw chunk embeddings (no Claude context) | `scripts/baseline_ingest.py` or `VectorDB.load_data()` |
| `regulations_openai_contextual` | Contextualized embeddings (**used by iteration 8**) | `ContextualVectorDB.load_data()` or `scripts/contextual_ingest.py` |

Iteration 8 connects to **`regulations_openai_contextual`** by default.

### Models used

| Role | Model | Provider |
|------|-------|----------|
| Embeddings | `text-embedding-3-small` | OpenAI |
| Contextualization (ingest) | `claude-haiku-4-5` (override: `RAG_CONTEXTUALIZE_MODEL`) | Anthropic |
| Answer generation (chat) | `claude-sonnet-4-5` | Anthropic |

Anthropic does not offer a general-purpose embedding model; this project follows
Anthropic's contextual-embeddings recipe but uses OpenAI for vectors.

---

## Environment setup

### Prerequisites

- Python **3.14+** (see `pyproject.toml`)
- [uv](https://docs.astral.sh/uv/) recommended, or pip
- API keys for **OpenAI** and **Anthropic**
- Jupyter (included in dependencies)

### Install dependencies

```bash
cd session-2
uv sync
```

This creates `.venv/` and installs all packages including **Gradio 6.x**,
ChromaDB, LangChain, Anthropic, and OpenAI SDKs.

### Jupyter kernel

In Jupyter, select kernel **`.venv`** (Python 3.14 from `session-2/.venv`).

If the kernel is missing:

```bash
cd session-2
uv run python -m ipykernel install --user --name=session-2 --display-name=".venv"
```

### Environment variables

Place `.env` in the **repository root** (`maven-classes/.env`). The notebooks
call `load_dotenv(find_dotenv())`, which walks up from the working directory.

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `OPENAI_API_KEY` | Yes | — | Embeddings |
| `ANTHROPIC_API_KEY` | Yes | — | Contextualization + chat |
| `RAG_TOKEN_BUDGET` | No | `50000` | Max tokens per chat session |
| `RAG_TIMEOUT_SECS` | No | `30` | Per-request Claude timeout |
| `RAG_LOG_FILE` | No | `rag_session_log.csv` | CSV query log path |
| `RAG_CONTEXTUALIZE_MODEL` | No | `claude-haiku-4-5` | Model for ingest contextualization |
| `RAG_MAX_DOC_TOKENS` | No | `80000` | Truncate very large PDFs for Claude |

---

## Building the vector index (one-time)

The Gradio app **does not contextualize at query time**. You must build the
index first.

### Option A — Notebook (iteration 7 or 8, cell 4)

Open `ragexperiment-7-class-architecture.ipynb` (or iteration 8), run cells
**1 → 2 → 3 → 4**:

```python
db = ContextualVectorDB(
    name="regulations_openai_contextual",
    data_dir=Path("data"),
    recursive=True,
)
db.load_data()
```

Expect **~2–3 hours** for all 32 PDFs (~2,823 Claude API calls). Progress prints
every 25 chunks per PDF; data is saved after each PDF completes.

### Option B — Headless script (recommended for long ingest)

```bash
cd session-2
uv run python scripts/contextual_ingest.py 2>&1 | tee logs/contextual_ingest.log
```

The script executes notebook cells 1–3 from iteration 7 and calls
`ContextualVectorDB.load_data()`. Monitor with:

```bash
tail -f logs/contextual_ingest.log
```

### Option C — Baseline only (fast, no contextualization)

For comparison / debugging retrieval without Claude situating:

```bash
cd session-2
uv run python scripts/baseline_ingest.py
```

Completes in ~20 seconds. Creates `regulations_openai_baseline` (not used by
iteration 8 by default).

### Verify the index

```bash
cd session-2
uv run python -c "
import chromadb
c = chromadb.PersistentClient('./data/chroma_store').get_collection('regulations_openai_contextual')
print('chunks:', c.count())
m = c.get(limit=1, include=['metadatas'])['metadatas'][0]
print('contextualized:', bool(m.get('contextualized_content')))
print('original stored:', bool(m.get('original_content')))
"
```

Expected output:

```
chunks: 2823
contextualized: True
original stored: True
```

---

## When to run what

Use this table to decide which notebook cells or scripts to execute.

| Goal | What to run | How often |
|------|-------------|-----------|
| **Use the Gradio chat app** | `ragexperiment-8-gradio-ui.ipynb` cells 1–3, 6 | Every session |
| **Build contextual index from scratch** | Iteration 7 cell 4 or `scripts/contextual_ingest.py` | Once (or after adding PDFs) |
| **Rebuild after adding new PDFs** | Same as above — incremental logic indexes only missing files | As needed |
| **Fast baseline index for experiments** | `scripts/baseline_ingest.py` | Optional |
| **Study pipeline evolution** | Notebooks 1–6 | Read-only / archival |
| **Terminal chat (no browser)** | Iteration 7 cells 1–3, 6 | Alternative to Gradio |

### Iteration 8 cell guide

| Cell | Purpose | Run when |
|------|---------|----------|
| **0** | Documentation | Read only |
| **1** | Imports + config | Every kernel restart |
| **2** | Heading regex helper | Every kernel restart |
| **3** | `VectorDB` / `ContextualVectorDB` classes | Every kernel restart |
| **4** | `db.load_data()` — full contextual ingest | **Only if index missing or re-ingesting** |
| **5** | Documentation | Read only |
| **6** | Gradio UI — `demo.launch()` | Every session (after 1–3) |

**Typical daily workflow:** restart kernel → run cells **1, 2, 3, 6** → use browser UI.

**Do not** run cell 4 if `regulations_openai_contextual` already has 2,823
chunks unless you intentionally want to re-ingest.

---

## Testing the Gradio UI (iteration 8)

This section is the **official test plan** for the final deliverable. Earlier
notebook iterations are not part of the acceptance test path.

### Pre-test checklist

- [ ] `uv sync` completed without errors
- [ ] `.env` in repo root with valid `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`
- [ ] Chroma index verified (2,823 contextual chunks — see above)
- [ ] Jupyter kernel set to `session-2/.venv`
- [ ] No other process using port 7860 (or Gradio will pick the next free port)

### Step 1 — Launch the application

1. Open `ragexperiment-8-gradio-ui.ipynb`
2. **Kernel → Restart**
3. Run cells in order: **1 → 2 → 3 → 6** (skip 4)
4. Wait for output similar to:

   ```
   VectorDB 'regulations_openai_contextual' ready — 2,823 chunks on disk
   Running on local URL:  http://127.0.0.1:7860
   ```

5. Click the URL or use the Jupyter-provided Gradio link

### Step 2 — Smoke test (UI loads)

- [ ] Page title shows **Municipal Regulations RAG**
- [ ] Header displays collection name, chunk count (~2,823), LLM model, token budget
- [ ] Chat panel, question text box, **Send** and **Clear chat** buttons visible
- [ ] **Retrieved passages** panel and **Token usage** field visible on the right

### Step 3 — Basic query test

Type a simple Baldwin-specific question, e.g.:

```
What are the requirements to install an alarm system in a business in the borough?
```

Click **Send**.

- [ ] Assistant reply appears in the chat within `RAG_TIMEOUT_SECS` (default 30s)
- [ ] Reply includes inline citations like `[1]`, `[2]`
- [ ] **Retrieved passages** panel populates with numbered sources (source path, heading, score, text)
- [ ] **Token usage** updates (turn tokens, session total, budget remaining)
- [ ] Question text box clears after send

### Step 4 — Multi-turn memory test

Without clicking **Clear chat**, ask a follow-up that depends on context:

```
Can you summarize the key permit or registration steps from that answer?
```

- [ ] Assistant responds coherently (uses prior turn in conversation history)
- [ ] Token usage **session total** increases across turns

### Step 5 — Allegheny County coverage test

Ask a question likely answered from county documents:

```
What are the air pollution control regulations for Allegheny County?
```

- [ ] Retrieved passages include sources under `alleghenycounty/` (not only `baldwin/`)
- [ ] Answer cites retrieved passages or states information is unavailable

### Step 6 — Out-of-corpus / refusal test

Ask something unrelated to municipal regulations:

```
What is the capital of France?
```

- [ ] Assistant refuses or states information is not in the provided documents (per system prompt rules)

### Step 7 — Clear chat test

Click **Clear chat**.

- [ ] Chat history empties
- [ ] Retrieved passages panel clears
- [ ] Token usage resets (session total back toward zero / budget fully remaining)

### Step 8 — Token budget test (optional)

Temporarily set a low budget in `.env`:

```env
RAG_TOKEN_BUDGET=1000
```

Restart kernel, re-run cells 1–3 and 6, send several detailed questions.

- [ ] After budget exhausted, new questions show a budget-exhausted message
- [ ] **Clear chat** resets budget and allows new questions

Restore `RAG_TOKEN_BUDGET=50000` when done.

### Step 9 — CSV logging test

After several queries, check `session-2/rag_session_log.csv`:

- [ ] File exists and grows with one row per query
- [ ] Columns include `timestamp`, `query`, `answer`, `tokens_turn`, chunk scores/sources/text

### Step 10 — Sample query battery

Use questions from `data/test_queries.txt` for broader coverage. Run at least
**5–10** queries across Baldwin and Allegheny topics:

```
do i have to register with the boro if i want to install an alarm?
what are the rules for parking on residential streets?
Can I put solar panels on my house roof? What are the steps for approval?
What is the overtime policy for the borough?
what is the noise ordinance in the borough?
```

For each query, spot-check:

- [ ] At least one retrieved passage looks relevant
- [ ] Citations in the answer map to passage numbers in the sources panel
- [ ] No obvious hallucination beyond retrieved text

### Step 11 — Stop the server

- Interrupt the Jupyter cell (■ Stop) or restart the kernel when testing is complete
- Gradio releases the local port

### Expected failures (not bugs)

| Symptom | Likely cause |
|---------|----------------|
| `NameError: ContextualVectorDB` | Cells 1–3 not run |
| `Collection has 0 chunks` | Index not built — run ingest (cell 4 or script) |
| Gradio message format error | Old cell 6 cached — re-run cell 6 after kernel restart |
| Timeout message | Increase `RAG_TIMEOUT_SECS` or simplify question |
| "Not available in the provided documents" | Valid — corpus may not contain that topic |

---

## Troubleshooting

### `db` / `ContextualVectorDB` not defined

Run cells **1–3** before cell 6. Iteration 8's Gradio cell uses `_get_db()` and
does not require cell 4.

### Ingest appears stuck

The first PDF (`Air Pollution Control.pdf`) has ~769 chunks. Chroma count stays
at 0 until that PDF finishes contextualizing. Watch for `chunk 25/769`
progress lines. Full ingest takes hours, not minutes.

### Re-ingest after accidental baseline load into contextual collection

`ContextualVectorDB.load_data()` detects missing `contextualized_content`
metadata and auto-resets the collection before re-indexing.

### Port already in use

Gradio auto-increments the port (`7861`, `7862`, …) or stop the previous
kernel run.

### ChromaDB locked / corrupt

Stop all notebooks using the index. As a last resort, delete `data/chroma_store/`
and re-run contextual ingest (destructive — rebuilds from scratch).

---

## Design decisions and trade-offs

| Decision | Rationale |
|----------|-----------|
| OpenAI embeddings + Anthropic LLM | OpenAI account available; Anthropic preferred for generation; no Voyage AI account |
| Contextualization at **ingest**, not query | Claude situating 2,823 chunks per session would be slow and expensive |
| Chroma `PersistentClient` | Index survives kernel restarts; iteration 6 used ephemeral in-memory storage |
| `original_content` in metadata | Embeddings use contextualized text; UI shows raw chunk for readable citations |
| Prompt caching (`cache_control: ephemeral`) | Anthropic API cache — unrelated to ChromaDB; ~99% cache read rate on full ingest |
| Gradio 6 message format | Chat history uses `{"role": "user"|"assistant", "content": "..."}` dicts |
| Incremental ingest | Only new PDFs are processed; safe to re-run after adding files |
| CSV session log | Enables offline analysis of retrieval quality and answers |

---

## Further reading

- [Anthropic Contextual Embeddings cookbook](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide)
- [ChromaDB persistence](https://docs.trychroma.com/docs/run/persistence)
- [Gradio documentation](https://www.gradio.app/docs)

---

*Session 2 final deliverable: `ragexperiment-8-gradio-ui.ipynb`*
