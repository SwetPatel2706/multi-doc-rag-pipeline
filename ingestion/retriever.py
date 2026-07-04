from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "multi_doc_eval"

class Retriever:
    def __init__(self, qdrant_url: str, qdrant_key: str):
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=60)
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        
    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Embeds the query text and retrieves the top_k closest chunks from Qdrant.
        """
        # Embed the query
        query_vector = self.model.encode(query_text).tolist()
        
        # Query Qdrant using query_points
        response = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )
        
        hits = []
        for point in response.points:
            payload = point.payload
            hits.append({
                "score": point.score,
                "text": payload.get("text"),
                "source": payload.get("source"),
                "type": payload.get("type"),
                "page": payload.get("page"),
                "slide": payload.get("slide"),
                "slide_end": payload.get("slide_end"),
                "title": payload.get("title")
            })
            
        return hits
