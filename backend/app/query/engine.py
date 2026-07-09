import logging
import time
from typing import Dict, Any, List

from app.query.planner import QueryPlanner
from app.query.retriever import HybridRetriever
from app.query.verifier import EvidenceVerifier
from app.query.synthesizer import AnswerSynthesizer

logger = logging.getLogger(__name__)

class QueryEngine:
    """
    Main entry point for natural language Q&A reasoning.
    Coordinates Query Planning, Hybrid Retrieval, Verification, and Synthesis.
    """

    def __init__(self):
        self.planner = QueryPlanner()
        self.retriever = HybridRetriever()
        self.verifier = EvidenceVerifier()
        self.synthesizer = AnswerSynthesizer()

    def ask(self, question: str) -> Dict[str, Any]:
        """
        Processes a natural language question and returns a cited response.
        """
        logger.info(f"Received query: '{question}'")
        start_time = time.time()

        # 1. Plan query decomposition and search strategy
        plan = self.planner.plan_query(question)

        # 2. Retrieve evidence from Qdrant and Neo4j
        retrieved_chunks = self.retriever.retrieve(plan)

        # 3. Verify retrieved chunks for relevance
        verified_chunks = self.verifier.verify_evidence(question, retrieved_chunks)

        # 4. Synthesize final response with inline citations
        answer, citations = self.synthesizer.synthesize(question, verified_chunks)

        elapsed_time = time.time() - start_time
        logger.info(f"Query processed in {elapsed_time:.2f} seconds.")

        # Clean chunks for UI consumption (exclude embeddings)
        clean_chunks = []
        for chunk in verified_chunks:
            clean_chunk = {
                "chunk_id": chunk.get("chunk_id"),
                "document_id": chunk.get("document_id"),
                "title": chunk.get("title"),
                "content": chunk.get("content"),
                "author": chunk.get("author"),
                "source": chunk.get("source"),
                "timestamp": chunk.get("timestamp"),
                "url": chunk.get("url"),
                "score": chunk.get("score")
            }
            clean_chunks.append(clean_chunk)

        return {
            "question": question,
            "plan": plan,
            "answer": answer,
            "citations": citations,
            "chunks_used": clean_chunks,
            "elapsed_seconds": round(elapsed_time, 2)
        }
