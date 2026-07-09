import os
import sys
from datetime import datetime, timezone

# Add backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.connectors.local_connector import LocalConnector
from app.connectors.github_connector import GitHubConnector
from app.connectors.gmail_connector import GmailConnector
from app.connectors.calendar_connector import CalendarConnector

def main():
    print("==================================================")
    print("Testing All 4 Connectors in Knowledge Detective")
    print("==================================================")

    # 1. Test Local Connector
    print("\n--- 1. Testing Local Connector ---")
    local_conn = LocalConnector()
    # Scan the backend/app/connectors/specs directory to test markdown parsing
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "connectors", "specs"))
    print(f"Scanning directory: {target_dir}")
    try:
        local_docs = local_conn.fetch_documents(target_dir)
        print(f"Success! Found {len(local_docs)} documents.")
        for d in local_docs[:2]:
            print(f"  * Title: {d.title} (Words: {len(d.content.split())})")
    except Exception as e:
        print(f"Local Connector Error: {e}")

    # 2. Test GitHub Connector
    print("\n--- 2. Testing GitHub Connector ---")
    github_conn = GitHubConnector()
    repo_name = "Sailesh3000/knowledge-detective"
    print(f"Fetching from public repo: {repo_name}")
    try:
        # Fetch only 1 item of each type to prevent rate limits
        github_docs = github_conn.fetch_documents(repo_name, limit=1)
        print(f"Success! Retrieved {len(github_docs)} GitHub items.")
        for d in github_docs:
            print(f"  * [{d.metadata.get('type')}] Title: {d.title} by @{d.author}")
    except Exception as e:
        print(f"GitHub Connector Error: {e}")

    # 3. Test Gmail Connector
    print("\n--- 3. Testing Gmail Connector ---")
    try:
        # Check if credentials exist
        creds_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))
        if not os.path.exists(creds_path):
            print("Skipping Gmail test: backend/credentials.json not found (needs GCP OAuth setup).")
        else:
            gmail_conn = GmailConnector()
            if gmail_conn.service:
                gmail_docs = gmail_conn.fetch_documents(limit=2)
                print(f"Success! Retrieved {len(gmail_docs)} emails.")
                for d in gmail_docs:
                    print(f"  * Subject: {d.title} (From: {d.author})")
            else:
                print("Gmail service could not initialize (requires credential consent).")
    except Exception as e:
        print(f"Gmail Connector Error: {e}")

    # 4. Test Google Calendar Connector
    print("\n--- 4. Testing Google Calendar Connector ---")
    try:
        creds_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "credentials.json"))
        if not os.path.exists(creds_path):
            print("Skipping Google Calendar test: backend/credentials.json not found.")
        else:
            calendar_conn = CalendarConnector()
            if calendar_conn.service:
                calendar_docs = calendar_conn.fetch_documents(limit=2)
                print(f"Success! Retrieved {len(calendar_docs)} calendar events.")
                for d in calendar_docs:
                    print(f"  * Event: {d.title} (Organizer: {d.author})")
            else:
                print("Calendar service could not initialize (requires credential consent).")
    except Exception as e:
        print(f"Calendar Connector Error: {e}")

    print("\n==================================================")
    print("Testing completed!")
    print("==================================================")

if __name__ == "__main__":
    main()
