# Verriffy

AI-assisted insurance claim analysis. Verriffy reads the documents and images of a claim, cross-checks them, and hands a human reviewer a **score, the reasons behind it, and the evidence for each reason**.

> **Status: early prototype, deployed but not fully verified.** The API is deployed and `GET /health` works. The full analysis has not been verified end to end with real claim data yet. See [Status](#status) and [Known limitations](#known-limitations).

## What it is (and is not)

- **Decision support, not a decision.** The score is a *review priority* (0-100). Verriffy never approves or rejects a claim and never says a claimant committed fraud. A human decides.
- **Evidence first.** Every finding must point to its source (file + page, or "Image n"). A finding without evidence is not reported.
- **Possible signs, not proof.** Image anomalies (edited-looking text, mismatched totals) are reported with a confidence level and are never treated as proof.

## Architecture

```
START -> IntroDecision --(unclear)--> END          (its reply is the chat answer)
              |
              +--(analyze_claim)--> LLM_ToolNode <--> tools      (collect data with tools)
                                        |
                                        +--(no more tools)--> text_analyzer  --+
                                        |                                       +--> combine_agent --> final_score --> END
                                        +--------------------> image_analyzer --+
```

Built with LangGraph. The analysis only starts when the client has clearly asked for it and given enough detail; normal chat never triggers it. `text_analyzer` and `image_analyzer` run **in parallel**; `combine_agent` waits for both.

| Graph node | File / function | Prompt (`prompts.py`) | Reads | Writes | What it does |
|---|---|---|---|---|---|
| `IntroDecision` | `intro_decision_node.py` / `IntroDecision_LLM` | `IntroDecision_Prompt` | `messages` | `messages`, `decision`, `RefindTopic` | Chats with the client; decides "unclear" (reply and stop) or "analyze_claim" (start) |
| `LLM_ToolNode` | `tool_calling_node.py` / `Tool_node_LLM` | `ToolCalling_Prompt` | `messages` | `messages` | Decides which tools to call to collect the claim data |
| `tools` | `tools.py` / `tools` | - | tool calls | `messages` | `rag_tool(query, claim_id)` searches that claim's documents and attaches the paths of the matching **original images** (`ToolMessage.artifact`) |
| `text_analyzer` | `text_analyzer_node.py` / `text_analyzer` | `TextAnalyzer_Prompt` | user text + tool results | `TextDATA` | Facts, issues, and the source of each |
| `image_analyzer` | `image_analyzer_node.py` / `image_analyzer` | `ImageAnalyzer_Prompt` | images the user sent + images found by `rag_tool` | `ImageDATA` | Per image: type, readable text, content, possible anomalies (the only node that looks at the original images with a vision model) |
| `combine_agent` | `combine_node.py` / `combine_agent` | `Combine_Prompt` | `TextDATA`, `ImageDATA` | `Dataprocess` | Matches, conflicts, missing facts, combined risk signals |
| `final_score` | `final_score_node.py` / `final_score` | `Final_Prompt` | `Dataprocess` | `Finaloutput` | Score, level, reasons with evidence, what to check next, confidence |

Shared state (`state.py`):

```python
class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    decision: str          # "analyze_claim" | "unclear", set by IntroDecision
    RefindTopic: str       # what to analyze, set by IntroDecision
    TextDATA: str
    ImageDATA: str
    Dataprocess: str
    Finaloutput: str
```

## Document ingestion (RAG)

`rag/ingestion.py` -> `RAG(path, claim_id)` indexes one PDF / DOCX / image for **one claim**:

- **One Pinecone namespace per claim** (`claim_id` = namespace), so a search can only reach that claim's documents. `claim_id` is validated (letters, digits, `-`, `_`, max 64).
- **Text:** chunked (1000 chars, 150 overlap) and embedded.
- **Images:** embedded images, scanned pages and chart pages of PDFs, images of DOCX files, and standalone images. Each image is **embedded directly** by `llama-nemotron-embed-vl-1b-v2` (text and images share one vector space). The original (shrunk to the API limit) is stored in **Postgres** (`rag_images` table), with a local cache in `IMAGE_DIR`.
- **Scanned pages** (little or no text layer) are transcribed once with the vision model so amounts and dates become searchable. The text carries a note that it may contain mistakes. Up to 10 pages per document; turn it off with `OCR_SCANNED_PAGES=0`.
- Same file content + same claim -> same ids, so uploading a file twice never duplicates. Limits: 15 MB per file, 150 PDF pages, 40 images per document.

`rag_tool` (`tools.py`): when a text chunk matches, the images of the same page come along (and the other way round).

**Who does what with images:** RAG only *stores and finds* them. The Image Analyzer is the node that *reads* them, from the original image. An embedding can only help to find an image; it cannot answer "what is the amount on this bill".

### Models (`models.py`)

Embeddings `nvidia/llama-nemotron-embed-vl-1b-v2`, reasoning / chat `z-ai/glm-5.3`, vision `meta/llama-3.2-90b-vision-instruct` (NVIDIA NIM via LangChain). Tracing with LangSmith.

## API (`main.py`)

Run locally: `uvicorn main:fastapi_app --reload` (interactive docs at `/docs`).

| Endpoint | Purpose |
|---|---|
| `GET /health` | `{"status": "healthy", "service": "verriffy-api"}` |
| `POST /chat?request=<text>&thread_id=<id>` | Both are **query parameters** (not a JSON body) and both are required. Returns `{"reply": "..."}` |

```bash
curl -X POST "http://localhost:8000/chat?request=hello&thread_id=demo-1"
```

Chat memory per `thread_id` is kept in Postgres when `DATABASE_URL` is set. Without it, every message is handled on its own (no memory).

Index a claim document from Python:

```python
from rag.ingestion import RAG

RAG("claims/discharge_summary.pdf", claim_id="CLAIM-1042")   # needs PINECONE_*, NVIDIA_API_KEY and DATABASE_URL
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in the values
```

| Variable | Needed for |
|---|---|
| `NVIDIA_API_KEY` | all models |
| `PINECONE_API_KEY`, `PINECONE_INDEX` | vector store (index dimension must match the embedding model) |
| `DATABASE_URL` | Postgres: stores original images and the chat memory |
| `langsmith` | LangSmith API key. `config.py` reads this exact name and `models.py` fails at import if it is missing |
| `IMAGE_DIR` (optional) | local image cache, default `images` |
| `OCR_SCANNED_PAGES` (optional) | `0` turns off the scanned-page transcription |

Never commit `.env`. Do not put real claim data in this repo.

## Status

| Area | State |
|---|---|
| Prompts, graph wiring, all nodes | Done, routing tested offline with stub models |
| RAG ingestion (text, images, OCR, claim namespaces, image storage in Postgres) | Written; not verified here against real Pinecone, Postgres and the real embedding model |
| API deployed (Render) | `GET /health` and `/docs` verified. A `POST /chat` test got **no response within 150-200 s** (cause not found: model latency, free-tier limits or a hang) |
| End-to-end analysis with real models and sample claims | **To do** |
| Insurance company data API tool | **To do** (`tools.py` TODO) |
| Upload endpoint (nothing in the API calls `RAG()` yet) | **To do** |
| Authentication | **To do** |

## Known limitations

- **No authentication.** Anyone who can reach the API can call the models. `claim_id` is supplied by the caller / the model and is not checked against a user, so access control per claim must be added before real use.
- **`POST /chat` returns only the last chat message.** The analysis result (`Finaloutput`) is written to the state but is not returned by the API yet.
- Without `DATABASE_URL` there is no chat memory and no image storage.
- Vision models can misread numbers; output is for human review and the original images must stay available.
- Llama-3.2-vision style models accept one image per request (the Image Analyzer sends one image per call, at most 6 per run).
- No audit log, no schema-validated score output, no evaluation set, no deterministic checks (amounts and dates are compared by the LLM, not by code), no metadata / duplicate-image checks.
- Scanned-page transcription adds vision calls to every upload.

## Roadmap

1. Find out why `/chat` does not answer; return `Finaloutput` from the API.
2. Authentication and per-user access to claims.
3. Upload endpoint that calls `RAG()`.
4. Insurance data API tool.
5. Structured output for the score; deterministic cross-document checks; image metadata and duplicate checks.
6. Audit trail (model, prompts, retrieved chunks, reviewer action) and reviewer UI.
7. Backtest on historical closed claims and measure outcomes (hours saved, leakage found, false positives).

## Repository layout

```
main.py                  FastAPI app (/health, /chat)
config.py                environment variables
graph.py                 LangGraph wiring
state.py                 shared State + IntroDecision schema
prompts.py               all system prompts
models.py                model clients (embeddings, chat, vision)
tools.py                 tools (rag_tool; insurance API tool TODO)
intro_decision_node.py   decides: chat reply or start analysis
tool_calling_node.py     collects data with tools
text_analyzer_node.py    text analysis node
image_analyzer_node.py   image analysis node
combine_node.py          cross-checks text vs images
final_score_node.py      score + reasons
rag/ingestion.py         indexing (text, images, OCR), image storage, vector store access
rag/image_utils.py       image shrinking / data-URL helpers
```
