# 📚 multi-doc-rag-pipeline

A modular, file-agnostic ingestion pipeline and basic evaluation suite designed to handle heterogeneous document sources (PDF and PPTX) and quantitatively assess retrieval quality in RAG applications.

```
Parser (PDF/PPTX) → Unified Intermediate Format → Chunker → Embedder → Qdrant Store → Evaluator
```

---

## What This Is

A backend-focused implementation of a **modular RAG ingestion pipeline**. It abstracts document parsing to process different file types (`.pdf` and `.pptx`) into a unified intermediate structure before chunking, embedding, and storing them in Qdrant. 

Additionally, it implements a structured, quantitative retrieval evaluation framework using a query-to-ground-truth mapping to compute retrieval hit rates.

**Key features:**
- 🧱 **Modular Architecture:** Structured into distinct layers: `parser/`, `chunker/`, `embedder/`, and `pipeline.py`.
- 📑 **Heterogeneous File Parsing:** Extract text slide-by-slide from PowerPoint presentations (`.pptx`) and page-by-page from documents (`.pdf`).
- 🔄 **Unified Intermediate representation:** Independent parser outputs (`{text, metadata}`) allow downstream chunking and embedding logic to operate blindly on the source document type.
- ⚡ **Local Embeddings:** Offline vector generation using `sentence-transformers` (`all-MiniLM-L6-v2`), producing 384-dimensional dense vectors.
- 🔍 **Vector DB Storage:** Local Qdrant instance integration via `qdrant-client`.
- 📊 **Automated Retrieval Evaluator:** Compares search results against a ground-truth dataset to compute a binary hit rate (retrieval accuracy), enabling empirical optimization of chunking strategies.

---

## Tech Stack

| Component | Library | Purpose & Notes |
|---|---|---|
| PDF Parsing | `pypdf` | Extracts page-based text content |
| PPTX Parsing | `python-pptx` | Extracts shape/text frame data slide-by-slide |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Offline 384-dim local embedding generation |
| Vector DB | `qdrant-client` | Vector store (Cosine similarity metric) |
| Coordination | `python-dotenv` | Configuration & environment variable loading |

---

## Project Structure

```
multi-doc-rag-pipeline/
├── ingestion/           # Pipeline component modules
│   ├── parser.py        # PDF & PPTX parsers (unifies output)
│   ├── chunker.py       # Handles text chunking strategies
│   └── embedder.py      # Manages local embedding generation
├── eval/                # Evaluation suite
│   ├── eval_queries.json # Ground-truth Q&A with source mapping
│   └── evaluator.py     # Evaluation executor (computes hit rate)
├── pipeline.py          # Main coordinator (runs ingestion & storage)
├── requirements.txt     # Python dependency definition
├── .env.example         # Template for environment configurations
├── NOTES.md             # Ingestion strategies comparison & dev log
└── PROJECT_3.md         # Original specification & requirements log
```

---

## Setup

### 1. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Environment variables
```bash
cp .env.example .env
```

Configure your local or cloud Qdrant URL and credentials in `.env`:
```env
QDRANT_URL=http://localhost:6333
# Or Qdrant Cloud credentials:
# QDRANT_URL=https://xxxx.us-east4-0.gcp.cloud.qdrant.io
# QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION=multi_doc_rag
```

---

## Ingestion & Pipeline Configuration

The pipeline parses documents into an intermediate dictionary structure:
```python
{
    "text": "Extracted string content...",
    "metadata": {
        "source": "filename.pdf",
        "type": "pdf",  # or "pptx"
        "page": 1       # or slide number
    }
}
```

### Running Ingestion
To run the full ingestion pipeline (parses, chunks, embeds, and uploads to Qdrant):
```bash
python pipeline.py --ingest --files "Gujarat State Road Transport Corporation - Wikipedia.pdf" "11-reasoning.pptx"
```

---

## Retrieval Evaluation

The pipeline features a dedicated evaluation suite to benchmark retrieval performance. A set of 10 ground-truth queries mapped to their specific source slide/page is stored in `eval/eval_queries.json`.

To run the evaluator:
```bash
python -m eval.evaluator --collection multi_doc_rag --top-k 3
```

This will run each evaluation query, perform a vector search, and compute the **Hit Rate @ K** (the percentage of queries where the ground-truth document source page/slide was returned within the top-k results).

---

## Ingestion Tuning Insights

A comprehensive breakdown of PPTX vs. PDF structural parsing difficulties, sliding window strategies, and comparative hit-rate results between `per-slide` and `multi-slide` chunking models can be found in [NOTES.md](file:///Users/swet/Developer/rag-prep/multi-doc-rag-pipeline/NOTES.md).
