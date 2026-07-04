import os
import uuid
from typing import List, Dict, Any
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "multi_doc_eval"

def embed_and_store(chunks: List[Dict[str, Any]], qdrant_url: str, qdrant_key: str):
    """
    Embeds text chunks locally using SentenceTransformer and uploads them to Qdrant Cloud.
    Clears the collection on start to ensure clean slate.
    """
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    print(f"Connecting to Qdrant Cloud at {qdrant_url}")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=60)
    
    print(f"Re-creating Qdrant collection: '{COLLECTION_NAME}'")
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
        
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qmodels.VectorParams(
            size=384, # all-MiniLM-L6-v2 dimension
            distance=qmodels.Distance.COSINE
        )
    )
    
    print(f"Embedding {len(chunks)} chunks...")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)
    
    # Convert numpy array to list if needed
    if not isinstance(embeddings, list):
        embeddings = embeddings.tolist()
        
    print("Uploading vectors to Qdrant Cloud...")
    points = []
    for i, chunk in enumerate(chunks):
        metadata = chunk["metadata"]
        # Generate a stable UUID based on chunk ID
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["id"]))
        
        payload = {
            "text": chunk["text"],
            "source": metadata["source"],
            "type": metadata["type"],
            "page": metadata.get("page"),     # None for PPTX
            "slide": metadata.get("slide"),    # None for PDF
            "slide_end": metadata.get("slide_end"), # None if per-slide or PDF
            "title": metadata.get("title"),    # None for PDF
        }
        
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=embeddings[i],
                payload=payload
            )
        )
        
    # Batch upload points
    batch_size = 100
    for start_idx in range(0, len(points), batch_size):
        end_idx = min(start_idx + batch_size, len(points))
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points[start_idx:end_idx]
        )
        
    print(f"  → Successfully stored {len(chunks)} vectors in Qdrant Cloud collection '{COLLECTION_NAME}'")
