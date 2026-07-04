from typing import List, Dict, Any

def chunk_pdf(pages: List[Dict[str, Any]], chunk_size: int = 400, overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Chunks PDF pages using a word-level sliding window.
    """
    chunks = []
    for page in pages:
        text = page["text"]
        metadata = page["metadata"]
        words = text.split()
        
        start = 0
        chunk_idx = 0
        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            
            # Construct chunk ID
            chunk_id = f"pdf_{metadata['source']}_p{metadata['page']}_c{chunk_idx}"
            
            # Copy metadata and add info
            chunk_metadata = metadata.copy()
            
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "metadata": chunk_metadata
            })
            
            chunk_idx += 1
            start += (chunk_size - overlap)
            if start >= len(words):
                break
                
    return chunks

def chunk_pptx(slides: List[Dict[str, Any]], strategy: str = "per-slide") -> List[Dict[str, Any]]:
    """
    Chunks PPTX slides based on strategy:
    - 'per-slide': Standalone chunk per slide
    - 'multi-slide': Sliding window of 2 slides (overlap of 1 slide)
    """
    chunks = []
    
    if strategy == "per-slide":
        for slide in slides:
            text = slide["text"]
            metadata = slide["metadata"]
            slide_num = metadata["slide"]
            title = metadata["title"]
            
            # Prepend Title for better embedding match
            formatted_text = f"Slide Title: {title}\n\n{text}"
            
            chunk_id = f"pptx_{metadata['source']}_s{slide_num}_per-slide"
            
            chunks.append({
                "id": chunk_id,
                "text": formatted_text,
                "metadata": metadata.copy()
            })
            
    elif strategy == "multi-slide":
        # Combine 2 consecutive slides: [i] and [i+1]
        for i in range(len(slides)):
            slide1 = slides[i]
            # If it's the last slide, we just output it alone or combine with previous?
            # To ensure it gets processed, if it's the last slide, we can combine with previous or output it. Let's do i+1 if possible.
            if i + 1 < len(slides):
                slide2 = slides[i+1]
                combined_text = (
                    f"Slide Title: {slide1['metadata']['title']}\n{slide1['text']}\n"
                    f"---\n"
                    f"Slide Title: {slide2['metadata']['title']}\n{slide2['text']}"
                )
                slide_num = slide1["metadata"]["slide"]
                chunk_id = f"pptx_{slide1['metadata']['source']}_s{slide_num}_multi-slide"
                
                # Metadata represents the start slide of the window
                combined_metadata = slide1["metadata"].copy()
                combined_metadata["slide_end"] = slide2["metadata"]["slide"]
                combined_metadata["title_end"] = slide2["metadata"]["title"]
                
                chunks.append({
                    "id": chunk_id,
                    "text": combined_text,
                    "metadata": combined_metadata
                })
            else:
                # Last slide alone
                formatted_text = f"Slide Title: {slide1['metadata']['title']}\n\n{slide1['text']}"
                slide_num = slide1["metadata"]["slide"]
                chunk_id = f"pptx_{slide1['metadata']['source']}_s{slide_num}_multi-slide"
                chunks.append({
                    "id": chunk_id,
                    "text": formatted_text,
                    "metadata": slide1["metadata"].copy()
                })
    else:
        raise ValueError(f"Unknown PPTX strategy: {strategy}")
        
    return chunks

def chunk_documents(documents: List[Dict[str, Any]], pptx_strategy: str = "per-slide") -> List[Dict[str, Any]]:
    """
    Type-aware chunking router. Dispatches to PDF or PPTX chunkers based on document metadata.
    """
    pdf_docs = [doc for doc in documents if doc["metadata"]["type"] == "pdf"]
    pptx_docs = [doc for doc in documents if doc["metadata"]["type"] == "pptx"]
    
    chunks = []
    if pdf_docs:
        chunks.extend(chunk_pdf(pdf_docs))
    if pptx_docs:
        chunks.extend(chunk_pptx(pptx_docs, strategy=pptx_strategy))
        
    print(f"Chunked documents with strategy: pdf=sliding-window, pptx={pptx_strategy}")
    print(f"  → Created {len(chunks)} chunks total")
    return chunks
