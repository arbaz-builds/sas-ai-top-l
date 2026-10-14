# Verriffy

AI-assisted insurance claim analysis. Verriffy reads the documents and images of a claim, cross-checks them, and hands a human reviewer a **score, the reasons behind it, and the evidence for each reason**.

> **Status: early prototype.** All agent nodes are written and the graph is wired and tested offline with stubbed models. It has **not** been run against real models or real claim data yet. See [Status](#status).

## What it is (and is not)

- **Decision support, not a decision.** The score is a *review priority* (0-100). Verriffy never approves or rejects a claim and never says a claimant committed fraud. A human decides.
- **Evidence first.** Every finding must point to its source (file + page, or "Image n"). A finding without evidence is not reported.
- **Possible signs, not proof.** Image anomalies (edited-looking text, mismatched totals) are reported with a confidence level and are never treated as proof.

## Architecture

```
START -> agent1 --(needs a tool)--> tools --+--> text_analyzer  --+
           |                                |                     +--> combine_agent --> final_score --> END
           +--(no tool needed)--> END       +--> image_analyzer --+
```

Built with LangGraph. `text_analyzer` and `image_analyzer` run **in parallel**; `combine_agent` waits for both.

| Node | File / function | Reads from state | Writes to state | What it does |
|---|---|---|---|---|
| Chat agent | `agent1.py` / `agent1` | `messages` | `messages` | Talks to the client, decides when to call a tool |
| Tools | `tool.py` / `tools` | tool calls | `messages` | `rag_tool` searches the indexed claim documents (Pinecone) |
| Text Analyzer | `text_analyzer.py` / `text_analyzer` | user text + tool results in `messages` | `TextDATA` | Extracts facts, finds issues, cites the source of each |
| Image Analyzer | `image_analyzer.py` / `image_analyzer` | images in `messages` | `ImageDATA` | Per image: type, readable text (OCR), content, possible anomalies |
| Combine Agent | `combion_agentm.py` / `combine_agent` | `TextDATA`, `ImageDATA` | `Dataprocess` | Matches, conflicts, missing facts, combined risk signals |
| Final Agent | `Final_agent.py` / `final_score` | `Dataprocess` | `Finaloutput` | Score, level, reasons with evidence, what to check next, confidence |

Prompts live in `system_prompt.py`. Shared state is defined in `agent_state.py`:

```python
class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    TextDATA: str
    ImageDATA: str
    Dataprocess: str
    Finaloutput: str
```

### Document ingestion (RAG)

`mmrag/rag.py` -> `RAG(path)`: PDF / DOCX -> LangChain loaders -> `RecursiveCharacterTextSplitter` (1000 chars, 150 overlap) -> embeddings -> Pinecone. `get_store()` returns the store used by `rag_tool`.

`mmrag/ingest.py` -> `image_data(path)`: image -> JPEG -> base64 data URL. Images reach the graph as `image_url` parts of a `HumanMessage`.

**Why images go to the vision model directly:** an embedding only helps to *find* an image, it cannot answer "what is the amount on this bill". The Image Analyzer therefore sends the original image to a vision model (one image per call, at most 6 per run, each shrunk to ~120 KB for the API limit).

### Stack

Python, LangGraph, LangChain, NVIDIA NIM (`ChatNVIDIA`, `NVIDIAEmbeddings`), Pinecone. Embedding model: `nvidia/llama-nemotron-embed-vl-1b-v2`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in the keys
```

Required in `.env`: `NVIDIA_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX` (the index dimension must match the embedding model).
Model names for the chat/reasoning model and the vision model are set in `LLM.py` (`resision_LLM`, `vision_LLM`).

Never commit `.env`. Do not put real claim data in this repo.

## Usage (example)

```python
from langchain_core.messages import HumanMessage
from graph import graph
from mmrag.ingest import image_data
from mmrag.rag import RAG

RAG("claims/discharge_summary.pdf")                      # index a document once

msg = HumanMessage(content=[
    {"type": "text", "text": "Please check my claim, the hospital bill is attached."},
    {"type": "image_url", "image_url": {"url": image_data("claims/bill.jpg")}},
])
result = graph.invoke({"messages": [msg]})
print(result["Finaloutput"])
```

Quick chat test: `python graph.py`.

Illustrative output shape (made-up values, not a real run):

```
SCORE: 72   LEVEL: high
REASONS:
 1. Bill total 7,000 INR (Image 1) differs from the claimed 5,000 INR (discharge_summary.pdf p.2)
 2. Possible edit around the total on Image 1 (confidence: low)
CHECK NEXT: ask the hospital for the original invoice; confirm the amount with the TPA record
CONFIDENCE: medium - one image partly unreadable
```

## Status

| Area | State |
|---|---|
| Node code (chat, text, image, combine, final) + prompts | Done |
| Graph wiring, parallel analyzers, fan-in | Done, tested offline with stub models |
| RAG ingestion function (PDF/DOCX -> Pinecone) | Written, not run against real Pinecone |
| Model names in `LLM.py` (`resision_LLM`, `vision_LLM`) | **To do**: empty; `vision_LLM` must be a `ChatNVIDIA` vision model |
| `Agent1_Prompt` (chat agent system prompt) | **To do**: empty |
| Insurance company data API tool | **To do** (`tool.py` TODO) |
| Upload / ingestion entry point | **To do**: nothing calls `RAG()` yet |
| End-to-end run with real models and sample claims | **To do** |

## Known limitations

- **No claim isolation yet.** Documents are not tagged with a `claim_id`, so different claims can mix in retrieval. Must be fixed before any real use.
- One tool round only: after the tool runs, analysis starts and `agent1` does not read the tool result. If `agent1` calls no tool, no analysis runs.
- Vision models can misread numbers. Original images must stay available to the reviewer; output is for human review.
- Llama-3.2-vision style models accept one image per request.
- No audit log, no structured (schema-validated) score output, no evaluation set yet.
- No deterministic checks yet (amount / date matching is done by the LLM, not by code).

## Roadmap

1. Fill in `LLM.py` models and `Agent1_Prompt`; run end-to-end on a few synthetic claims.
2. Add `claim_id` metadata / Pinecone namespaces for claim isolation.
3. Upload + ingestion entry point.
4. Insurance data API tool.
5. Structured output for the score; deterministic cross-document checks in code.
6. Audit trail (model, prompts, retrieved chunks, reviewer action) and reviewer UI.
7. Backtest on historical closed claims and measure outcomes (hours saved, leakage found, false positives).

## Repository layout

```
graph.py             LangGraph wiring
agent1.py            chat agent (tool calling)
text_analyzer.py     text analysis node
image_analyzer.py    image analysis node
combion_agentm.py    combine node (cross-check text vs images)
Final_agent.py       score + reasons node
agent_state.py       shared State
system_prompt.py     all prompts
LLM.py               model clients (embeddings, chat, vision)
tool.py              tools (rag_tool; insurance API tool TODO)
mmrag/rag.py         document ingestion + vector store access
mmrag/ingest.py      image -> data URL
```

Leftovers from an earlier design, unused and pending removal: `main.py`, `mmrag/api.py`, `mmrag/clients.py`, `mmrag/config.py`, `mmrag/store.py`, `tests/`.
