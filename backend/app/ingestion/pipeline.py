import logging
from app.models.document import Document
from app.ingestion.chunker import Chunker
from app.ingestion.embedder import Embedder
from app.ingestion.metadata_extractor import MetadataExtractor
from app.ingestion.graph_builder import GraphBuilder

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """
    Orchestrates the ingestion workflow:
    Document -> Chunk -> Embed -> Qdrant -> Metadata Extractor (LLM) -> Neo4j.
    """

    def __init__(self):
        self.chunker = Chunker()
        self.embedder = Embedder()
        self.extractor = MetadataExtractor()
        self.graph_builder = GraphBuilder()

    def ingest_document(self, doc: Document) -> bool:
        """
        Ingests a single document through the vector and graph indexing pipeline.
        Performs transactional deletes first to prevent duplicates on update.
        """
        logger.info(f"Starting ingestion pipeline for document '{doc.id}' (Source: {doc.source.value}, Title: '{doc.title}')")

        try:
            # 1. Clean up any existing instances of this document to prevent duplicates
            self.delete_document(doc.id)

            # 2. Chunk text content
            chunks = self.chunker.split_document(doc)
            if not chunks:
                logger.warning(f"Document '{doc.id}' was parsed into 0 chunks. Skipping Qdrant vector storage.")
            else:
                # 3. Compute embeddings & store in Qdrant
                qdrant_success = self.embedder.store_chunks(chunks)
                if not qdrant_success:
                    logger.error(f"Failed to store vector chunks for document '{doc.id}' in Qdrant.")
                    # Continue anyway, we still try graph builder

            # 4. Extract semantic metadata (entities & relations) using local LLM
            # Since Ollama might be offline or slow, we wrap this in a safe block
            extracted_metadata = {"entities": [], "relationships": []}
            try:
                # Use a snippet of the document to extract metadata to avoid LLM context blowup
                # Usually first 8000 characters is plenty for architectural context
                snippet_for_llm = doc.content[:8000]
                extracted_metadata = self.extractor.extract_metadata(
                    content=snippet_for_llm,
                    title=doc.title,
                    source=doc.source.value,
                    author=doc.author
                )
            except Exception as llm_err:
                logger.error(f"LLM Metadata extraction failed for doc '{doc.id}': {str(llm_err)}. Continuing with empty metadata.")

            # 5. Store nodes and edges in Neo4j
            graph_success = self.graph_builder.store_document_nodes(doc, extracted_metadata)
            if not graph_success:
                logger.error(f"Failed to store graph nodes for document '{doc.id}' in Neo4j.")

            logger.info(f"Ingestion pipeline completed for document '{doc.id}'.")
            return True

        except Exception as e:
            logger.error(f"Ingestion pipeline crashed for document '{doc.id}': {str(e)}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Deletes a document's traces from both Qdrant and Neo4j.
        """
        logger.debug(f"Cleaning up indexing for document '{doc_id}'...")
        qdrant_ok = self.embedder.delete_document_chunks(doc_id)
        neo4j_ok = self.graph_builder.delete_document_nodes(doc_id)
        return qdrant_ok and neo4j_ok

    def close(self):
        """
        Closes database connection drivers.
        """
        self.graph_builder.close()
