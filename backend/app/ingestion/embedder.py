import uuid
import logging
from typing import List, Optional
# pyrefly: ignore [missing-import]
from qdrant_client import QdrantClient
# pyrefly: ignore [missing-import]
from qdrant_client.http.models import Distance, VectorParams, PointStruct
# pyrefly: ignore [missing-import]
from sentence_transformers import SentenceTransformer
from app.config import settings
from app.models.document import DocumentChunk

logger = logging.getLogger(__name__)

class Embedder:
    """
    Computes vector embeddings using SentenceTransformers and stores them in Qdrant.
    """
    _model = None
    _qdrant_client = None

    def __init__(self):
        # Lazy load model to avoid overhead if not actively embedding
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self.collection_name = "document_chunks"

    @property
    def model(self) -> SentenceTransformer:
        if Embedder._model is None:
            try:
                # pyrefly: ignore [missing-import]
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                if device == "cuda":
                    logger.info("ROCm/CUDA GPU detected! Loading SentenceTransformer model on GPU acceleration...")
                else:
                    logger.info("ROCm/CUDA GPU not detected. Loading SentenceTransformer model on CPU...")
                Embedder._model = SentenceTransformer(self.model_name, device=device)
                logger.info("SentenceTransformer model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {str(e)}")
                raise e
        return Embedder._model

    @property
    def qdrant_client(self) -> QdrantClient:
        if Embedder._qdrant_client is None:
            logger.info(f"Connecting to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}...")
            try:
                Embedder._qdrant_client = QdrantClient(
                    host=settings.QDRANT_HOST, 
                    port=settings.QDRANT_PORT,
                    timeout=10.0
                )
                self._ensure_collection()
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant vector database: {str(e)}")
                raise e
        return Embedder._qdrant_client

    def _ensure_collection(self):
        """
        Creates the Qdrant document collection if it does not exist.
        """
        try:
            # Check if collection exists
            exists = Embedder._qdrant_client.collection_exists(self.collection_name)
            if not exists:
                logger.info(f"Qdrant collection '{self.collection_name}' does not exist. Creating it...")
                Embedder._qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 output dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection '{self.collection_name}' created successfully.")
            else:
                logger.debug(f"Qdrant collection '{self.collection_name}' already exists.")
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection: {str(e)}")
            raise e

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector representation for a list of string contents.
        """
        if not texts:
            return []
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise e

    def store_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """
        Computes embeddings for a list of DocumentChunks and upserts them into Qdrant.
        """
        if not chunks:
            return True

        try:
            # 1. Extract texts and compute embeddings
            texts = [c.content for c in chunks]
            embeddings = self.generate_embeddings(texts)
            
            points = []
            for i, chunk in enumerate(chunks):
                chunk.embedding = embeddings[i]
                
                # 2. Generate a stable UUID from chunk string ID
                qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.id))
                
                # 3. Create payload
                payload = chunk.metadata.copy()
                payload.update({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index
                })
                
                points.append(PointStruct(
                    id=qdrant_id,
                    vector=chunk.embedding,
                    payload=payload
                ))

            # 4. Upsert into Qdrant collection
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Successfully indexed {len(chunks)} chunks in Qdrant collection '{self.collection_name}'.")
            return True

        except Exception as e:
            logger.error(f"Failed to store chunks in Qdrant: {str(e)}")
            return False

    def delete_document_chunks(self, document_id: str) -> bool:
        """
        Removes all chunks associated with a specific parent document ID from Qdrant.
        Useful when updating or deleting a local file.
        """
        try:
            # pyrefly: ignore [missing-import]
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
            logger.info(f"Deleted existing chunks for document '{document_id}' from Qdrant.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document chunks from Qdrant: {str(e)}")
            return False

    def search_similar_chunks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Searches Qdrant for chunks semantically similar to the query.
        """
        try:
            query_vector = self.generate_embeddings([query])[0]
            hits = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            results = []
            for hit in hits:
                if hit.payload:
                    payload = hit.payload.copy()
                    payload["score"] = hit.score
                    results.append(payload)
            return results
        except Exception as e:
            logger.error(f"Failed to search similar chunks: {str(e)}")
            return []

    def fetch_chunks_by_document_id(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Fetches all chunks from Qdrant belonging to a specific document ID.
        """
        try:
            # pyrefly: ignore [missing-import]
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            hits, _ = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=100
            )
            return [hit.payload for hit in hits if hit.payload]
        except Exception as e:
            logger.error(f"Failed to fetch chunks by document ID: {str(e)}")
            return []
