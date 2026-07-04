import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ingestion.parsers.pdf_parser import parse_pdf
from ingestion.parsers.pptx_parser import parse_pptx
from ingestion.chunker import chunk_documents
from ingestion.embedder import embed_and_store
from ingestion.retriever import Retriever

load_dotenv()

def run_ingest(pdf_paths, pptx_paths, pptx_strategy):
    """
    Ingests all specified PDF and PPTX files, chunks them, embeds them,
    and stores them in the Qdrant Cloud collection 'multi_doc_eval'.
    """
    documents = []

    # 1. Parse PDFs
    if pdf_paths:
        for path in pdf_paths:
            if not os.path.exists(path):
                print(f"Error: PDF file not found at {path}")
                sys.exit(1)
            parsed_pages = parse_pdf(path)
            documents.extend(parsed_pages)

    # 2. Parse PPTXs
    if pptx_paths:
        for path in pptx_paths:
            if not os.path.exists(path):
                print(f"Error: PPTX file not found at {path}")
                sys.exit(1)
            parsed_slides = parse_pptx(path)
            documents.extend(parsed_slides)

    if not documents:
        print("Error: No documents provided to ingest.")
        sys.exit(1)

    # 3. Chunk
    print(f"\nChunking documents using PPTX strategy: {pptx_strategy}")
    chunks = chunk_documents(documents, pptx_strategy=pptx_strategy)

    # 4. Embed and Store
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url or not qdrant_key:
        print("Error: QDRANT_URL and QDRANT_API_KEY must be set in the environment.")
        sys.exit(1)

    embed_and_store(chunks, qdrant_url, qdrant_key)
    print("\nIngestion pipeline complete!")

def run_query(query_text, top_k):
    """
    Performs a semantic query on the ingested collection and prints results.
    """
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url or not qdrant_key:
        print("Error: QDRANT_URL and QDRANT_API_KEY must be set in the environment.")
        sys.exit(1)

    retriever = Retriever(qdrant_url, qdrant_key)
    hits = retriever.query(query_text, top_k=top_k)

    print(f"\nSemantic search results for: '{query_text}'")
    print("=" * 80)
    for i, hit in enumerate(hits, start=1):
        source_info = ""
        if hit["type"] == "pdf":
            source_info = f"[PDF p.{hit['page']}]"
        elif hit["type"] == "pptx":
            slide_range = f"slide {hit['slide']}"
            if hit.get("slide_end"):
                slide_range += f"-{hit['slide_end']}"
            source_info = f"[PPTX {slide_range} | Title: {hit['title']}]"

        print(f"Hit #{i} (Score: {hit['score']:.4f}) {source_info} from {hit['source']}")
        # Indent lines of text
        indented_text = "\n".join("  " + line for line in hit["text"].split("\n"))
        print(indented_text)
        print("-" * 80)

def run_eval(eval_file_path, top_k):
    """
    Runs the manual evaluation loop over the 10 Q&A pairs in the eval set.
    """
    if not os.path.exists(eval_file_path):
        print(f"Error: Evaluation set file not found at {eval_file_path}")
        sys.exit(1)

    with open(eval_file_path, "r") as f:
        eval_set = json.load(f)

    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url or not qdrant_key:
        print("Error: QDRANT_URL and QDRANT_API_KEY must be set in the environment.")
        sys.exit(1)

    retriever = Retriever(qdrant_url, qdrant_key)
    passed_count = 0

    print(f"\nRunning evaluation on {len(eval_set)} Q&A pairs (top_k={top_k})...")
    print("=" * 100)

    for i, item in enumerate(eval_set, start=1):
        question = item["question"]
        expected_type = item.get("expected_type", "single")
        
        print(f"\nQ{i}: {question}")
        
        hits = retriever.query(question, top_k=top_k)
        
        is_hit = False
        matching_hit = None
        
        for hit in hits:
            # Check matching logic
            if expected_type == "cross-source":
                expected_sources = item.get("expected_sources", [])
                if hit["source"] in expected_sources:
                    is_hit = True
                    matching_hit = hit
                    break
            else:
                expected_source = item.get("expected_source")
                expected_location = item.get("expected_location", {})
                
                if hit["source"] == expected_source:
                    loc_type = expected_location.get("type")
                    if loc_type == "pdf":
                        if hit["page"] == expected_location.get("page"):
                            is_hit = True
                            matching_hit = hit
                            break
                    elif loc_type == "pptx":
                        target_slide = expected_location.get("slide")
                        start_slide = hit["slide"]
                        end_slide = hit.get("slide_end")
                        
                        # Match if target slide matches start_slide,
                        # or if slide_end exists and target slide falls in range [start_slide, end_slide]
                        if end_slide:
                            if start_slide <= target_slide <= end_slide:
                                is_hit = True
                                matching_hit = hit
                                break
                        else:
                            if start_slide == target_slide:
                                is_hit = True
                                matching_hit = hit
                                break

        if is_hit:
            passed_count += 1
            source_info = ""
            if matching_hit["type"] == "pdf":
                source_info = f"page {matching_hit['page']}"
            else:
                slide_range = f"slide {matching_hit['slide']}"
                if matching_hit.get("slide_end"):
                    slide_range += f"-{matching_hit['slide_end']}"
                source_info = f"{slide_range} ('{matching_hit['title']}')"
            print(f"  ✅ PASS: Found correct source in top-{top_k} (Hit score: {matching_hit['score']:.4f}, located in {matching_hit['source']} {source_info})")
        else:
            print(f"  ❌ FAIL: Correct source/location not found in top-{top_k} hits.")
            print("  Top retrieved items were:")
            for rank, hit in enumerate(hits, start=1):
                source_loc = f"p.{hit['page']}" if hit['type'] == 'pdf' else f"s.{hit['slide']}"
                if hit.get('slide_end'):
                    source_loc += f"-{hit['slide_end']}"
                print(f"    {rank}. {hit['source']} ({source_loc}) - Score: {hit['score']:.4f}")

    hit_rate = passed_count / len(eval_set) if eval_set else 0.0
    print("\n" + "=" * 100)
    print(f"EVALUATION SUMMARY: {passed_count}/{len(eval_set)} passed | Hit Rate @ {top_k} = {hit_rate:.1%}")
    print("=" * 100)

def main():
    parser = argparse.ArgumentParser(description="Multi-Document RAG Ingestion & Evaluation CLI")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ingest", action="store_true", help="Run document ingestion")
    group.add_argument("--query", type=str, help="Query the RAG system semantic store")
    group.add_argument("--eval", type=str, help="Path to evaluation JSON set")
    
    # Ingestion arguments
    parser.add_argument("--pdf", action="append", default=[], help="Path to PDF file to ingest")
    parser.add_argument("--pptx", action="append", default=[], help="Path to PPTX file to ingest")
    parser.add_argument("--pptx-strategy", choices=["per-slide", "multi-slide"], default="per-slide",
                        help="Chunking strategy for PPTX files (default: per-slide)")
    
    # Query / Eval arguments
    parser.add_argument("--top-k", type=int, default=5, help="Number of hits to retrieve (default: 5)")
    
    args = parser.parse_args()
    
    if args.ingest:
        if not args.pdf and not args.pptx:
            print("Error: Specify at least one --pdf or --pptx file when using --ingest.")
            sys.exit(1)
        run_ingest(args.pdf, args.pptx, args.pptx_strategy)
    elif args.query:
        run_query(args.query, args.top_k)
    elif args.eval:
        run_eval(args.eval, args.top_k)

if __name__ == "__main__":
    main()
