import logging
from typing import List, Dict, Any, Set
from app.ingestion.embedder import Embedder
from app.ingestion.graph_builder import GraphBuilder

logger = logging.getLogger(__name__)

class HybridRetriever:
    """
    Orchestrates retrieval of evidence chunks from both Qdrant (semantic vector search)
    and Neo4j (graph relations/traversals).
    """

    def __init__(self):
        self.embedder = Embedder()
        self.graph_builder = GraphBuilder()

    def retrieve(self, plan: Dict[str, Any], limit_per_query: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves matching chunks based on the query plan.
        """
        search_type = plan.get("search_type", "hybrid")
        sub_queries = plan.get("sub_queries", [])
        entities = plan.get("entities", [])
        topics = plan.get("topics", [])

        evidence_chunks: Dict[str, Dict[str, Any]] = {}

        # 1. Semantic Vector Search
        if search_type in ["vector", "hybrid"]:
            for sub_query in sub_queries:
                logger.info(f"Running vector search for: '{sub_query}'...")
                hits = self.embedder.search_similar_chunks(sub_query, limit=limit_per_query)
                for hit in hits:
                    chunk_id = hit.get("chunk_id")
                    if chunk_id and chunk_id not in evidence_chunks:
                        evidence_chunks[chunk_id] = hit

        # 2. Graph Relation Search
        if search_type in ["graph", "hybrid"]:
            doc_ids_from_graph: Set[str] = set()
            
            with self.graph_builder.driver.session() as session:
                # Search by entities/topics (mentions)
                for item in entities + topics:
                    logger.info(f"Searching graph for entity/topic mentions: '{item}'...")
                    query = """
                    MATCH (d:Document)-[:MENTIONS]->(e)
                    WHERE toLower(e.name) CONTAINS toLower($search_term)
                    RETURN d.id as doc_id
                    UNION
                    MATCH (p:Person)-[:AUTHORED|ATTENDED]->(d:Document)
                    WHERE toLower(p.name) CONTAINS toLower($search_term) 
                       OR any(alias IN p.aliases WHERE toLower(alias) CONTAINS toLower($search_term))
                    RETURN d.id as doc_id
                    """
                    result = session.run(query, search_term=item.strip())
                    for record in result:
                        doc_ids_from_graph.add(record["doc_id"])

            # Pull chunks for retrieved document IDs from Qdrant
            for doc_id in doc_ids_from_graph:
                logger.info(f"Graph path matched document '{doc_id}'. Fetching chunks...")
                chunks = self.embedder.fetch_chunks_by_document_id(doc_id)
                for chunk in chunks:
                    chunk_id = chunk.get("chunk_id")
                    if chunk_id and chunk_id not in evidence_chunks:
                        # Give graph-matched chunks a baseline relevance score
                        chunk["score"] = chunk.get("score", 0.75)
                        evidence_chunks[chunk_id] = chunk

        # 3. Sort by score descending and return
        sorted_evidence = sorted(
            evidence_chunks.values(),
            key=lambda x: x.get("score", 0.0),
            reverse=True
        )
        
        logger.info(f"Retrieved {len(sorted_evidence)} total unique evidence chunks.")
        return sorted_evidence
