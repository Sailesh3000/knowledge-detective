import os
import sys

# Add backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.connectors.local_connector import LocalConnector

def main():
    connector = LocalConnector()
    print("Scanning workspace folder for documents...")
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    docs = connector.fetch_documents(workspace_dir)
    
    print(f"\nFound {len(docs)} document(s):")
    for doc in docs:
        print(f"\n- Title: {doc.title}")
        print(f"  Source: {doc.source}")
        print(f"  ID: {doc.id}")
        print(f"  Timestamp: {doc.timestamp}")
        print(f"  Author: {doc.author}")
        print(f"  URL: {doc.url}")
        print(f"  Word count: {len(doc.content.split())}")
        print(f"  File type: {doc.metadata.get('file_type')}")
        print(f"  First 100 chars content: {doc.content[:100].strip()}...")

if __name__ == "__main__":
    main()
