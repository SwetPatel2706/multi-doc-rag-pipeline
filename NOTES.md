# Multi-Document Ingestion & Evaluation Notes

## Why PPTX Chunking is Genuinely Harder Than PDF

### 1. Structural Difference (Prose vs. Bullet Fragments)
PDFs contain continuous prose, forming natural sentences and paragraph structures. Traditional word-level sliding windows work extremely well because sentences flow logically.
PPTX slides contain fragmented bullet points, text boxes, and visuals.
- **Example from CS224W Slide 5 (Today: Reasoning over KGs):**
  The raw text extracted:
  `Today: Reasoning over KGs | | Goal: | How to perform multi-hop reasoning over KGs? | Reasoning over Knowledge Graphs | Answering multi-hop queries | Path Queries | Conjunctive Queries | Query2Box | 10/28/24 | Jure Leskovec, Stanford CS224W...`
  These are list fragments with no connective verbs. A sentence-transformer model might struggle with vocabulary alignment or contextual flow because the syntax is sparse and disjoint.

### 2. Lack of Context (Sparse Slides)
Slides often refer to diagrams or assume implicit context from preceding slides.
- **Example from CS224W Slide 21 (General Idea):**
  It lists a high-level summary of Query2Box box embeddings but doesn't explain the math. Slide 22 might contain the math, but if parsed individually, Slide 21 lacks the formulas while Slide 22 lacks the definitions.
- **Example from Slide 2 (Announcements):**
  Without knowing it is an announcement slide for CS224W, a statement like `10/31: Homework 3 released` has no context (what class? what topic?). In `per-slide`, the title "Announcements" and general slide text got retrieved but with a low score (0.2415).

### 3. Missing/Merged Text (Layout Extraction Noise)
Unlike clean PDF flows, PPTX shapes can be placed anywhere. The reading order of shapes in `python-pptx` (which follows the shape index tree) does not always match the visual reading order (top-to-bottom, left-to-right). This leads to out-of-order text.

---

## Ingestion & Evaluation Results

We ran evaluation on our 10 Q&A pairs (mix of PDF, PPTX, and cross-source) using two PPTX chunking strategies:

### Strategy 1: `per-slide` (Baseline)
- **Description:** Each slide is its own chunk. The slide's title is prepended to the body text.
- **Evaluation Hit Rate:** **100% (10/10)**
- **Observations:** Very clean and granular. However, individual slides had lower search scores on sparse questions.
  - *Example:* Q7 ("What was released on October 31 according to the announcements slide?") retrieved Slide 2 with a low score of **0.2415**.

### Strategy 2: `multi-slide` (Optimized)
- **Description:** Consecutive slides are grouped in pairs (Slide N and N+1) with a sliding overlap of 1 slide.
- **Evaluation Hit Rate:** **100% (10/10)**
- **Observations:** Scores on PPTX queries slightly shifted.
  - *Example:* Q7 ("What was released on October 31...") retrieved Slide 1-2 with a score of **0.2149**.
  - Although the hit rate remained at 100%, grouping slides provides more surrounding context (e.g. if the answer is on slide N, we also capture slide N+1's details, which is highly beneficial for generation).

---

## Domain Mismatch and Eval Quality Note

Because the PDF topic (Ahmedabad / GSRTC transit) and the PPTX topic (Stanford CS224W Graph Representation Learning / Reasoning) are completely distinct, the cross-source evaluation queries ("Where is the GSRTC headquarters or central office located?") represent a search across two totally disjoint domains.
- A high hit rate here indicates the pipeline successfully separates distinct domains and routes queries correctly.
- However, it does not test fine-grained retrieval ranking among overlapping topic domains (e.g. distinguishing between two different slides on "Conjunctive Queries"). This is a limitation to address when building the final Capstone RAG system.

---

## What We'd Change for the Capstone Ingestion Service

1. **Robust Layout-Aware Reading Order:** For PPTX, sort text shapes by their coordinates `(top, left)` to ensure text is read in standard visual order rather than arbitrary creation order.
2. **Context Enrichment via LLM:** Generate summaries/titles for sparse slides or pages using Gemini before storing them, especially for image-heavy slides.
3. **Hybrid Search:** Combine Dense (SentenceTransformers) and Sparse (BM25) search to capture both exact terminology matches (e.g. "GSRTC", "Query2Box") and conceptual matches.
4. **Mean Reciprocal Rank (MRR):** Move from binary hit rate to MRR or NDCG to penalize hits that appear lower in the top-k results (e.g. ranking at #5 vs. #1).
