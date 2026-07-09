import os
import sys

# Add backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.connectors.github_connector import GitHubConnector

def main():
    # If GITHUB_TOKEN is available, PyGithub will use it.
    connector = GitHubConnector()
    
    # We can test with octocat/Spoon-Knife (very lightweight) or Sailesh3000/knowledge-detective
    repo_name = "Sailesh3000/knowledge-detective"
    print(f"Connecting to GitHub and fetching data for {repo_name}...")
    
    # Fetch 3 of each type
    docs = connector.fetch_documents(repo_name, limit=3)
    
    print(f"\nFetched {len(docs)} document(s) from GitHub:")
    
    # Group by type
    by_type = {}
    for doc in docs:
        doc_type = doc.metadata.get("type", "unknown")
        by_type.setdefault(doc_type, []).append(doc)
        
    for doc_type, items in by_type.items():
        print(f"\n--- {doc_type.upper()} ({len(items)} items) ---")
        for doc in items[:3]:
            print(f"- Title: {doc.title}")
            print(f"  Author: {doc.author}")
            print(f"  Timestamp: {doc.timestamp}")
            print(f"  URL: {doc.url}")
            print(f"  Word Count: {len(doc.content.split())}")
            print(f"  First 100 chars content:\n  {doc.content[:150].strip()}...\n")

if __name__ == "__main__":
    main()
