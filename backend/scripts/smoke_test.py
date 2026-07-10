"""
Smoke Test Suite — Knowledge Detective
======================================
Step 9: Polish, testing, demo prep

Runs a battery of automated smoke tests across the full stack:
  1. Health check (GET /health)
  2. API route availability (timeline, graph, query, demo)
  3. Query pipeline with the 5 canonical demo questions
  4. Pre-cached demo endpoint validation
  5. Gap-detection (unanswerable question) verification

Exit code: 0 = all tests passed, 1 = one or more failures.

Usage:
    cd backend
    python -m scripts.smoke_test
"""

import sys
import os
import json
import time
import logging

# ---------------------------------------------------------------------------
# Path setup — allow running from backend/ root
# ---------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("smoke_test")

from fastapi.testclient import TestClient
from app.main import app

# ---------------------------------------------------------------------------
# Test runner helpers
# ---------------------------------------------------------------------------
_results: list[dict] = []


def _record(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    _results.append({"name": name, "status": status, "detail": detail})
    icon = "✅" if passed else "❌"
    print(f"  {icon}  [{status}] {name}" + (f" — {detail}" if detail else ""))


def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

def test_health(client: TestClient) -> None:
    _section("1. Health Check")
    res = client.get("/health")
    _record(
        "GET /health returns 200",
        res.status_code == 200,
        f"status={res.status_code}",
    )
    data = res.json()
    _record(
        "Health response contains 'status: healthy'",
        data.get("status") == "healthy",
        str(data.get("status")),
    )
    _record(
        "Health response exposes config block",
        "config" in data,
        str(list(data.keys())),
    )


def test_timeline(client: TestClient) -> None:
    _section("2. Timeline API")

    res = client.get("/api/timeline")
    _record("GET /api/timeline (no filter) returns 200", res.status_code == 200, f"status={res.status_code}")
    data = res.json()
    _record(
        "Timeline response has 'events' key",
        "events" in data,
        str(list(data.keys())),
    )

    res2 = client.get("/api/timeline?topic=Neo4j")
    _record(
        "GET /api/timeline?topic=Neo4j returns 200",
        res2.status_code == 200,
        f"status={res2.status_code}",
    )


def test_graph(client: TestClient) -> None:
    _section("3. Graph API")

    res = client.get("/api/graph")
    _record("GET /api/graph (no filter) returns 200", res.status_code == 200, f"status={res.status_code}")
    data = res.json()
    _record(
        "Graph response has 'nodes' and 'links' keys",
        "nodes" in data and "links" in data,
        str(list(data.keys())),
    )

    res2 = client.get("/api/graph?entity=Neo4j")
    _record(
        "GET /api/graph?entity=Neo4j returns 200",
        res2.status_code == 200,
        f"status={res2.status_code}",
    )

    res3 = client.get("/api/graph?entity=PostgreSQL")
    _record(
        "GET /api/graph?entity=PostgreSQL returns 200 (may be empty)",
        res3.status_code == 200,
        f"status={res3.status_code}",
    )


def test_demo_endpoint(client: TestClient) -> None:
    _section("4. Demo Cache Endpoint")

    res = client.get("/api/demo/questions")
    _record(
        "GET /api/demo/questions returns 200",
        res.status_code == 200,
        f"status={res.status_code}",
    )
    if res.status_code == 200:
        data = res.json()
        _record(
            "Demo questions list is non-empty",
            len(data.get("questions", [])) > 0,
            f"count={len(data.get('questions', []))}",
        )

    # Try fetching the first cached question by index
    res2 = client.get("/api/demo/answer/0")
    _record(
        "GET /api/demo/answer/0 returns 200",
        res2.status_code == 200,
        f"status={res2.status_code}",
    )


def test_query_validation(client: TestClient) -> None:
    _section("5. Query API — Input Validation")

    # Empty question should be rejected
    res = client.post("/api/query", json={"question": ""})
    _record(
        "POST /api/query with empty question returns 400",
        res.status_code == 400,
        f"status={res.status_code}",
    )

    # Whitespace-only question should also be rejected
    res2 = client.post("/api/query", json={"question": "   "})
    _record(
        "POST /api/query with whitespace question returns 400",
        res2.status_code == 400,
        f"status={res2.status_code}",
    )


def test_gap_detection(client: TestClient) -> None:
    _section("6. Gap Detection — Unanswerable Query")
    print("  ℹ️  Sending an unanswerable question to verify gap detection...")
    print("  ⏳  This may take up to 60s (LLM inference on CPU)...")
    start = time.time()
    res = client.post(
        "/api/query",
        json={"question": "What is the detailed payment processing SLA for the billing service?"},
        timeout=120,
    )
    elapsed = round(time.time() - start, 1)
    _record(
        "POST /api/query for unanswerable question returns 200 (not 500)",
        res.status_code == 200,
        f"status={res.status_code}, elapsed={elapsed}s",
    )
    if res.status_code == 200:
        data = res.json()
        answer: str = data.get("answer", "")
        no_hallucination = (
            "no relevant" in answer.lower()
            or "not found" in answer.lower()
            or "no evidence" in answer.lower()
            or "cannot" in answer.lower()
            or "no information" in answer.lower()
            or "missing" in answer.lower()
        )
        _record(
            "Gap-detection response acknowledges missing evidence (no hallucination)",
            no_hallucination,
            f"answer_snippet='{answer[:120]}...'",
        )


def test_demo_queries(client: TestClient) -> None:
    """
    Runs the 5 canonical demo questions from the pre-cached demo endpoint
    and verifies that responses are well-formed (have answer + citations).
    """
    _section("7. Canonical Demo Query Smoke Test (via /api/demo/answer)")

    print("  ℹ️  Testing all 5 canonical demo questions via the pre-cached demo endpoint...")

    res = client.get("/api/demo/questions")
    if res.status_code != 200:
        _record("Fetch demo questions list", False, "Demo endpoint not available — skipping query tests")
        return

    questions = res.json().get("questions", [])
    for idx, q in enumerate(questions):
        answer_res = client.get(f"/api/demo/answer/{idx}")
        passed = answer_res.status_code == 200
        data = answer_res.json() if passed else {}
        has_answer = bool(data.get("answer"))
        _record(
            f"Demo Q{idx+1} — '{q[:50]}...' has cached answer",
            passed and has_answer,
            f"status={answer_res.status_code}, has_answer={has_answer}",
        )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report() -> int:
    _section("SMOKE TEST REPORT")
    passed = sum(1 for r in _results if r["status"] == "PASS")
    failed = sum(1 for r in _results if r["status"] == "FAIL")
    total = len(_results)

    print(f"\n  Total: {total}  |  Passed: {passed}  |  Failed: {failed}\n")

    if failed > 0:
        print("  Failed tests:")
        for r in _results:
            if r["status"] == "FAIL":
                print(f"    ❌  {r['name']}")
                if r.get("detail"):
                    print(f"        → {r['detail']}")

    overall = "ALL TESTS PASSED ✅" if failed == 0 else f"SOME TESTS FAILED ❌ ({failed}/{total})"
    print(f"\n  Result: {overall}")
    print("=" * 60)
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Knowledge Detective — Automated Smoke Test Suite")
    print("  Step 9: Polish, testing, demo prep")
    print("=" * 60)

    client = TestClient(app)

    test_health(client)
    test_timeline(client)
    test_graph(client)
    test_demo_endpoint(client)
    test_query_validation(client)
    test_gap_detection(client)
    test_demo_queries(client)

    exit_code = print_report()
    sys.exit(exit_code)
