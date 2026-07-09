import sys
import os
import json
import logging

# Ensure backend root is in search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_api")

from fastapi.testclient import TestClient
from app.main import app

def run_api_tests():
    print("\n==================================================")
    print("Step 7: Testing API Routes via FastAPI TestClient")
    print("==================================================")

    client = TestClient(app)

    # 1. Test /health
    print("\n--- [GET /health] ---")
    res = client.get("/health")
    print(f"Status Code: {res.status_code}")
    print(json.dumps(res.json(), indent=2))
    assert res.status_code == 200

    # 2. Test GET /api/timeline (unfiltered)
    print("\n--- [GET /api/timeline] (Unfiltered) ---")
    res = client.get("/api/timeline")
    print(f"Status Code: {res.status_code}")
    data = res.json()
    print(f"Total events found: {len(data.get('events', []))}")
    if data.get("events"):
        print("First Event sample:")
        print(json.dumps(data["events"][0], indent=2))
    assert res.status_code == 200

    # 3. Test GET /api/timeline (filtered)
    print("\n--- [GET /api/timeline?topic=Neo4j] (Filtered) ---")
    res = client.get("/api/timeline?topic=Neo4j")
    print(f"Status Code: {res.status_code}")
    data = res.json()
    print(f"Filtered events found: {len(data.get('events', []))}")
    if data.get("events"):
        print("First Event sample:")
        print(json.dumps(data["events"][0], indent=2))
    assert res.status_code == 200

    # 4. Test GET /api/graph (unfiltered)
    print("\n--- [GET /api/graph] (Unfiltered) ---")
    res = client.get("/api/graph")
    print(f"Status Code: {res.status_code}")
    data = res.json()
    print(f"Nodes count: {len(data.get('nodes', []))}, Links count: {len(data.get('links', []))}")
    if data.get("nodes"):
        print("Sample Node:")
        print(json.dumps(data["nodes"][0], indent=2))
    if data.get("links"):
        print("Sample Link:")
        print(json.dumps(data["links"][0], indent=2))
    assert res.status_code == 200

    # 5. Test GET /api/graph (filtered)
    print("\n--- [GET /api/graph?entity=PostgreSQL] (Filtered) ---")
    res = client.get("/api/graph?entity=PostgreSQL")
    print(f"Status Code: {res.status_code}")
    data = res.json()
    print(f"Filtered Nodes count: {len(data.get('nodes', []))}")
    assert res.status_code == 200

    # 6. Test POST /api/query
    print("\n--- [POST /api/query] ---")
    query_payload = {"question": "Why did we choose Neo4j over PostgreSQL?"}
    print(f"Sending query: '{query_payload['question']}' (this might take up to 2 min on CPU)...")
    res = client.post("/api/query", json=query_payload)
    print(f"Status Code: {res.status_code}")
    
    if res.status_code == 200:
        data = res.json()
        print("\nAPI Answer response:")
        print(data.get("answer"))
        print("\nCitations:")
        print(json.dumps(data.get("citations", []), indent=2))
    else:
        print(f"Failed with detail: {res.text}")
    assert res.status_code == 200

    print("\n==================================================")
    print("API route verification complete and correct!")
    print("==================================================")

if __name__ == "__main__":
    run_api_tests()
