import os
import json
import logging
from datetime import datetime, timezone
from app.config import settings
from app.models.document import Document, SourceType
from app.connectors.local_connector import LocalConnector
from app.ingestion.pipeline import IngestionPipeline

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_pipeline")

def load_synthetic_emails() -> list[Document]:
    """
    Reads email JSON files from test-data/emails and parses them into Documents.
    """
    emails_dir = os.path.join(settings.TEST_DATA_DIR, "emails")
    documents = []
    
    if not os.path.exists(emails_dir):
        logger.error(f"Emails test directory does not exist: {emails_dir}")
        return documents

    for filename in os.listdir(emails_dir):
        if not filename.endswith(".json"):
            continue
            
        file_path = os.path.join(emails_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Parse RFC date or fallback
            try:
                # E.g. "Sun, 01 Jun 2026 11:00:00 +0000"
                import email.utils
                dt = email.utils.parsedate_to_datetime(data["date"])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = datetime.now(timezone.utc)
                
            content = f"From: {data['from']}\nTo: {data['to']}\nDate: {data['date']}\nSubject: {data['subject']}\n\n{data['body']}"
            
            doc = Document(
                id=f"gmail_{data['id']}",
                source=SourceType.GMAIL,
                title=data["subject"],
                content=content,
                url=f"https://mail.google.com/mail/u/0/#inbox/{data['threadId']}",
                timestamp=dt,
                author=data["from"],
                metadata={
                    "message_id": data["id"],
                    "thread_id": data["threadId"],
                    "labels": data.get("labelIds", []),
                    "type": "email"
                }
            )
            documents.append(doc)
        except Exception as e:
            logger.error(f"Failed to load synthetic email {filename}: {str(e)}")
            
    logger.info(f"Loaded {len(documents)} synthetic emails from {emails_dir}")
    return documents

def test_ingestion():
    # 1. Instantiate connectors and pipeline
    local_conn = LocalConnector()
    pipeline = IngestionPipeline()
    
    print("\n==================================================")
    print("Step 5: Testing Ingestion Pipeline over Synthetic Data")
    print("==================================================")
    
    # 2. Reset Databases for a clean test
    print("\n--- Resetting Databases ---")
    try:
        # Wipe Qdrant collection
        client = pipeline.embedder.qdrant_client
        if client.collection_exists(pipeline.embedder.collection_name):
            print(f"Recreating Qdrant collection: {pipeline.embedder.collection_name}")
            client.delete_collection(pipeline.embedder.collection_name)
        pipeline.embedder._ensure_collection()
        print("Qdrant collection wiped and recreated.")
    except Exception as q_err:
        print(f"Warning: Failed to reset Qdrant: {str(q_err)}")

    try:
        # Wipe Neo4j Graph
        with pipeline.graph_builder.driver.session() as session:
            print("Wiping Neo4j Graph database...")
            session.run("MATCH (n) DETACH DELETE n")
        print("Neo4j database fully wiped.")
    except Exception as n_err:
        print(f"Warning: Failed to reset Neo4j: {str(n_err)}")

    # 3. Load synthetic documents, meetings, and emails
    print("\n--- Loading Synthetic Datasets ---")
    docs_path = os.path.join(settings.TEST_DATA_DIR, "docs")
    meetings_path = os.path.join(settings.TEST_DATA_DIR, "meetings")
    
    local_docs = local_conn.fetch_documents(docs_path)
    meetings = local_conn.fetch_documents(meetings_path)
    # Remap source and metadata for meetings so they are treated as SourceType.CALENDAR
    calendar_meetings = []
    for m in meetings:
        # Extract attendees from meeting body if present
        attendees = []
        for line in m.content.splitlines():
            if line.startswith("**Attendees:**"):
                # E.g. "**Attendees:** Sailesh, Tejas, Abhilash"
                attendees = [a.strip() for a in line.split(":", 1)[1].split(",")]
                break
                
        m.source = SourceType.CALENDAR
        m.metadata["type"] = "meeting"
        m.metadata["attendees"] = attendees
        calendar_meetings.append(m)
        
    emails = load_synthetic_emails()

    all_docs = local_docs + calendar_meetings + emails
    print(f"Total documents prepared for ingestion: {len(all_docs)}")
    print(f"  * Local Docs: {len(local_docs)}")
    print(f"  * Meetings (Calendar): {len(calendar_meetings)}")
    print(f"  * Emails (Gmail): {len(emails)}")

    # 4. Ingest documents sequentially
    print("\n--- Running Ingestion Pipeline ---")
    success_count = 0
    for doc in all_docs:
        print(f"Ingesting: {doc.title} ({doc.source.value})...")
        success = pipeline.ingest_document(doc)
        if success:
            success_count += 1
            
    print(f"\nIngested {success_count} / {len(all_docs)} documents successfully.")

    # 5. Database Verification Stats
    print("\n--- Verifying Ingestion Stats ---")
    
    # Qdrant verify
    try:
        col_info = pipeline.embedder.qdrant_client.get_collection(pipeline.embedder.collection_name)
        vector_count = col_info.points_count
        print(f"Qdrant collection '{pipeline.embedder.collection_name}' has {vector_count} vector chunks.")
    except Exception as q_stat_err:
        print(f"Error fetching Qdrant counts: {str(q_stat_err)}")

    # Neo4j verify
    try:
        with pipeline.graph_builder.driver.session() as session:
            node_counts = session.run(
                """
                MATCH (n) 
                RETURN labels(n)[0] as label, count(n) as count 
                ORDER BY count DESC
                """
            )
            print("\nNeo4j Nodes:")
            for record in node_counts:
                print(f"  * {record['label'] or 'Unlabeled'}: {record['count']}")
                
            edge_counts = session.run(
                """
                MATCH ()-[r]->() 
                RETURN type(r) as type, count(r) as count 
                ORDER BY count DESC
                """
            )
            print("\nNeo4j Relationships:")
            for record in edge_counts:
                print(f"  * {record['type']}: {record['count']}")
    except Exception as n_stat_err:
        print(f"Error fetching Neo4j counts: {str(n_stat_err)}")

    # Cleanup connections
    pipeline.close()
    print("\n==================================================")
    print("Testing completed!")
    print("==================================================")

if __name__ == "__main__":
    test_ingestion()
