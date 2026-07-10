"""
Query Test — 5 Canonical Demo Questions
=========================================
Step 9: Polish, testing, demo prep

Runs the 5 canonical demo questions through the LIVE query engine and
compares output quality against expected criteria.  This complements the
smoke test (which hits the pre-cached demo endpoint) by verifying that
the actual LLM + retrieval pipeline produces coherent, cited, non-hallucinated
answers.

Expected run time: 5–15 min on CPU (each question triggers Ollama inference).

Usage:
    cd backend
    python -m scripts.query_test
"""

import sys
import os
import json
import time
import logging

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("query_test")

from app.query.engine import QueryEngine

# ---------------------------------------------------------------------------
# Test definitions
# ---------------------------------------------------------------------------
# Each entry: (question, description, acceptance_checks)
# acceptance_checks is a list of (description, callable(response) -> bool)

DEMO_QUESTIONS = [
    (
        "Why did we choose Neo4j over PostgreSQL?",
        "Cross-source decision tracing — expects cited answer from email + meeting notes + local doc",
        [
            ("Answer is non-empty", lambda r: bool(r["answer"].strip())),
            ("Answer is not an error message", lambda r: "error" not in r["answer"].lower()[:50]),
            ("At least 1 citation returned", lambda r: len(r["citations"]) >= 1),
            ("Plan identifies Neo4j as an entity", lambda r: any("neo4j" in e.lower() for e in r["plan"].get("entities", []))),
            ("Elapsed time is reasonable (< 180s)", lambda r: r["elapsed_seconds"] < 180),
        ],
    ),
    (
        "What has Sailesh been working on this week?",
        "Person-centric graph traversal — expects answer referencing PRs / issues authored by Sailesh",
        [
            ("Answer is non-empty", lambda r: bool(r["answer"].strip())),
            ("Answer does not claim no documents found (some Sailesh content should be indexed)", lambda r: "no relevant" not in r["answer"].lower()[:80]),
            ("At least 1 citation returned", lambda r: len(r["citations"]) >= 1),
            ("Plan identifies Sailesh as an entity", lambda r: any("sailesh" in e.lower() for e in r["plan"].get("entities", []))),
        ],
    ),
    (
        "Show me the timeline of the authentication decision",
        "Chronological chain — expects answer with multiple dated sources",
        [
            ("Answer is non-empty", lambda r: bool(r["answer"].strip())),
            ("At least 1 citation returned", lambda r: len(r["citations"]) >= 1),
            ("Plan identifies authentication-related entities or topics", lambda r: (
                any("auth" in e.lower() for e in r["plan"].get("entities", []))
                or any("auth" in t.lower() for t in r["plan"].get("topics", []))
            )),
        ],
    ),
    (
        "What's the status of the frontend?",
        "Status/progress query — expects answer referencing React, Vite, or frontend PRs",
        [
            ("Answer is non-empty", lambda r: bool(r["answer"].strip())),
            ("At least 1 citation returned", lambda r: len(r["citations"]) >= 1),
        ],
    ),
    (
        "What is the detailed payment processing SLA for the billing service?",
        "Gap detection — unanswerable question; expects explicit 'no evidence' / 'not found' response",
        [
            ("Answer is non-empty (not silent failure)", lambda r: bool(r["answer"].strip())),
            (
                "Answer acknowledges missing evidence (gap detection)",
                lambda r: any(
                    phrase in r["answer"].lower()
                    for phrase in [
                        "no relevant",
                        "not found",
                        "no evidence",
                        "no information",
                        "cannot",
                        "missing",
                        "knowledge gap",
                    ]
                ),
            ),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_query_tests() -> int:
    """
    Runs all demo questions through the live query engine.
    Returns 0 if all tests pass, 1 if any fail.
    """
    print("\n" + "=" * 70)
    print("  Knowledge Detective — Live Query Test (5 Canonical Demo Questions)")
    print("  Step 9: Polish, testing, demo prep")
    print("=" * 70)

    engine = QueryEngine()
    total_passed = 0
    total_failed = 0
    total_checks = 0

    for q_idx, (question, description, checks) in enumerate(DEMO_QUESTIONS):
        print(f"\n{'─'*70}")
        print(f"  Q{q_idx + 1} of {len(DEMO_QUESTIONS)}: {question}")
        print(f"  Purpose: {description}")
        print(f"{'─'*70}")
        print("  ⏳  Running query (may take 30–120s on CPU)...")

        start = time.time()
        try:
            response = engine.ask(question)
            elapsed = round(time.time() - start, 1)
            print(f"  ✅  Response received in {elapsed}s")
            print(f"\n  Plan:")
            print(f"    search_type : {response['plan'].get('search_type', '?')}")
            print(f"    entities    : {response['plan'].get('entities', [])}")
            print(f"    topics      : {response['plan'].get('topics', [])}")
            print(f"\n  Answer (first 300 chars):")
            print(f"    {response['answer'][:300]}...")
            print(f"\n  Citations ({len(response.get('citations', []))} total):")
            for cite in response.get("citations", [])[:3]:
                print(f"    * [{cite.get('source', '?').upper()}] {cite.get('title', 'Untitled')} (by {cite.get('author', '?')})")
            if len(response.get("citations", [])) > 3:
                print(f"    ... and {len(response['citations']) - 3} more")

            print(f"\n  Acceptance Checks:")
            q_passed = 0
            q_failed = 0
            for check_desc, check_fn in checks:
                try:
                    passed = check_fn(response)
                except Exception as check_err:
                    passed = False
                    check_desc += f" [ERROR: {check_err}]"
                icon = "✅" if passed else "❌"
                status = "PASS" if passed else "FAIL"
                print(f"    {icon} [{status}] {check_desc}")
                if passed:
                    q_passed += 1
                    total_passed += 1
                else:
                    q_failed += 1
                    total_failed += 1
                total_checks += 1

            print(f"\n  Result: {q_passed}/{len(checks)} checks passed for Q{q_idx + 1}")

        except Exception as exc:
            elapsed = round(time.time() - start, 1)
            print(f"  ❌  Query FAILED after {elapsed}s: {exc}")
            logger.exception(f"Query engine raised an exception for question: {question}")
            # Count all checks as failures
            for _ in checks:
                total_failed += 1
                total_checks += 1

    # ---------------------------------------------------------------------------
    # Summary report
    # ---------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print(f"  QUERY TEST REPORT")
    print(f"{'='*70}")
    print(f"  Questions tested  : {len(DEMO_QUESTIONS)}")
    print(f"  Total checks      : {total_checks}")
    print(f"  Passed            : {total_passed}")
    print(f"  Failed            : {total_failed}")

    if total_failed == 0:
        print("\n  Result: ALL CHECKS PASSED ✅")
        print("=" * 70)
        return 0
    else:
        pass_rate = round(100 * total_passed / total_checks, 1) if total_checks else 0
        print(f"\n  Result: {total_failed} CHECK(S) FAILED ❌  (pass rate: {pass_rate}%)")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = run_query_tests()
    sys.exit(exit_code)
