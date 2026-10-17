# Verriffy

AI-assisted insurance claim analysis. Verriffy reads the documents and images of a claim, cross-checks them, and hands a human reviewer a **score, the reasons behind it, and the evidence for each reason**.

> **Status: early prototype.** All nodes and prompts are written and the graph is wired. It has **not** been run against real models or real claim data yet, and the intro node is not finished. See [Status](#status).

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
| `IntroDecision` | `intro_decision_node.py` / `IntroDecision_LLM` | `IntroDecision_Prompt` | `messages` | `messages`, `decision` | Chats with the client; decides "unclear" (reply and stop) or "analyze_claim" (start) |
| `LLM_ToolNode` | `tool_calling_node.py` / `Tool_node_LLM` | `ToolCalling_Prompt` | `messages` | `messages` | Decides which tools to call to collect the claim data |
| `tools` | `tools.py` / `tools` | - | tool calls | `messages` | `rag_tool` searches the indexed claim documents (text and image descriptions, optional `claim_id` filter) and attaches the **original images** it finds (`ToolMessage.artifact`) |
| `text_analyzer` | `text_analyzer_node.py` / `text_analyzer` | `TextAnalyzer_Prompt` | user text + tool results | `TextDATA` | Facts, issues, and the source of each |
| `image_analyzer` | `image_analyzer_node.py` / `image_analyzer` | `ImageAnalyzer_Prompt` | images the user sent + images found by `rag_tool` | `ImageDATA` | Per image: type, readable text (OCR), content, possible anomalies |
| `combine_agent` | `combine_node.py` / `combine_agent` | `Combine_Prompt` | `TextDATA`, `ImageDATA` | `Dataprocess` | Matches, conflicts, missing facts, combined risk signals |
| `final_score` | `final_score_node.py` / `final_score` | `Final_Prompt` | `Dataprocess` | `Finaloutput` | Score, level, reasons with evidence, what to check next, confidence |

Shared state is in `state.py` (`State`, plus the `IntroDecision` structured-output schema):

```python
class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    TextDATA: str
    ImageDATA: str
    Dataprocess: str
    Finaloutput: str
```
`graph.py` reads `state["decision"]` to route after `IntroDecision` (see Status: this field still has to be added to `State`).

### Document ingestion (RAG)

`rag/ingestion.py` -> `RAG(path, claim_id=None)` indexes one file for one claim, **text and images**. No vision model is used here:

- **Text:** PDF / DOCX -> LangChain loaders -> `RecursiveCharacterTextSplitter` (1000 chars, 150 overlap) -> embeddings -> Pinecone.
- **Images:** embedded images of PDF / DOCX, scanned PDF pages and chart-heavy pages (rendered to an image), and standalone image files. The **original** is saved (`IMAGE_DIR`, default `data/images`; later S3) and the image itself is **embedded directly** by `llama-nemotron-embed-vl-1b-v2` (it reads text and images in the same vector space), so a text question can find an image.
- **Metadata** on every chunk: `source`, `page` (starts at 1), `type` (`text` / `image`), `claim_id`, and `image_path` for images. Chunk ids are deterministic, so indexing the same file again overwrites instead of duplicating.

`rag_tool` (`tools.py`) searches with an optional `claim_id` filter. On a mixed page a text hit also brings the images of that page, and an image hit brings the text of that page. The paths of the original images travel in `ToolMessage.artifact`.

**Who does what with images:** RAG only *stores and finds* them. The **Image Analyzer** is the only node with a vision model: it looks at the original images (the ones the user sent and the ones `rag_tool` found) and reads their text, content and possible anomalies. An embedding can only help to *find* an image; it cannot answer "what is the amount on this bill".

`rag/image_utils.py`: `image_data(path)` (image -> base64 data URL) and helpers that shrink images to the API size limit (one image per vision call, at most 6 per run, ~120 KB each).

### Stack

Python, LangGraph, LangChain, NVIDIA NIM (`ChatNVIDIA`, `NVIDIAEmbeddings`), Pinecone. Embedding model: `nvidia/llama-nemotron-embed-vl-1b-v2`. Model clients live in `models.py`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in the keys
```

Required in `.env`: `NVIDIA_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX` (the index dimension must match the embedding model). Model names are set in `models.py`. Optional: `IMAGE_DIR` (where original images are kept).

Never commit `.env`. Do not put real claim data in this repo.

## Usage (example)

Works once the intro node is finished (see Status).

```python
from langchain_core.messages import HumanMessage
from graph import graph
from rag.image_utils import image_data
from rag.ingestion import RAG

RAG("claims/discharge_summary.pdf")                      # index a document once

msg = HumanMessage(content=[
    {"type": "text", "text": "Please analyze claim C-1042. The hospital bill is attached."},
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
| All system prompts (`prompts.py`, 6) | Done |
| Graph wiring (`graph.py`): intro decision, tool loop, parallel analyzers, fan-in | Done; every import resolves; routing tested offline with stub models |
| Analyzer, combine and final nodes | Done, tested offline with stub models |
| RAG ingestion (text + images embedded directly, `claim_id`, same-page images) and `rag_tool` | Done, tested offline with a fake store and fake embeddings; **not yet run against real Pinecone / the real embedding model** (image embedding through `NVIDIAEmbeddings` must be confirmed with a real key) |
| `IntroDecision` node (`intro_decision_node.py`) | **To do**: use `with_structured_output`; return the reply as an `AIMessage` and store `decision` in state |
| `decision` field in `State` | **To do** (graph routing reads it) |
| `vision_LLM` in `models.py` | **To do**: must be a vision chat model (`ChatNVIDIA`), currently empty |
| Insurance company data API tool | **To do** (`tools.py` TODO) |
| Upload / ingestion entry point | **To do**: nothing calls `RAG()` yet |
| End-to-end run with real models and sample claims | **To do** |

## Known limitations

- **Claim isolation depends on `claim_id`.** Chunks are tagged and `rag_tool` can filter, but the model has to pass `claim_id` (the prompt tells it to). Without it, all claims are searched. It should be enforced in code before any real use.
- Indexing a file again overwrites its chunks, but chunks of a *shorter* new version are not removed.
- Vision models can misread numbers. Original images must stay available to the reviewer; output is for human review.
- Llama-3.2-vision style models accept one image per request.
- No audit log, no structured (schema-validated) score output, no evaluation set yet.
- No deterministic checks yet (amount / date matching is done by the LLM, not by code).

## Roadmap

1. Finish `IntroDecision`, add `decision` to `State`, set `vision_LLM`; run end-to-end on a few synthetic claims.
2. Enforce claim isolation in code (Pinecone namespaces per claim) instead of relying on the model to pass `claim_id`.
3. Upload + ingestion entry point.
4. Insurance data API tool.
5. Structured output for the score; deterministic cross-document checks in code.
6. Audit trail (model, prompts, retrieved chunks, reviewer action) and reviewer UI.
7. Backtest on historical closed claims and measure outcomes (hours saved, leakage found, false positives).

## Repository layout

```
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
rag/ingestion.py         document + image ingestion (images embedded directly), vector store access
rag/image_utils.py       image -> data URL, image shrinking
```
