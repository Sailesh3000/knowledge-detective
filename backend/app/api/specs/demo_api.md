# Demo API — Specification

> **Status**: Implemented (Step 9 — Polish, testing, demo prep)
>
> Exposes two read-only endpoints that serve pre-cached, high-quality query
> responses for a reliable live demo experience. No LLM inference is triggered.

---

## Why a Demo Cache?

Live LLM inference can take 30–120 seconds on CPU, which is impractical
during a timed hackathon presentation. The demo cache pre-builds answers for
the 5 canonical demonstration questions and serves them instantly, while
preserving **identical response schema** with the live `/api/query` endpoint.

The cache also acts as a regression baseline: if the live query engine
produces degraded output, the demo cache guarantees a polished fallback.

---

## Data Source

Pre-cached responses are stored in:

```
backend/data/demo_cache.json
```

The file is a JSON array of objects. Each object has the same schema as the
response from `POST /api/query`, plus:

| Extra Field | Value  | Purpose                                        |
|-------------|--------|------------------------------------------------|
| `_cached`   | `true` | Signals to the frontend that this is from cache |

The cache is loaded **once at startup** (module import). If the file is
missing, both endpoints return `503 Service Unavailable`.

---

## Endpoints

### `GET /api/demo/questions`

Returns the list of all pre-built demo question strings, indexed by their
position in the cache array.

**Response (200 OK)**

```json
{
  "questions": [
    "Why did we choose Neo4j over PostgreSQL?",
    "What has Sailesh been working on this week?",
    "Show me the timeline of the authentication decision",
    "What's the status of the frontend?",
    "Who decided to use Qdrant and why?"
  ],
  "count": 5,
  "note": "Use GET /api/demo/answer/{index} to retrieve a full cached response."
}
```

**Error Responses**

| Status | Condition                    |
|--------|------------------------------|
| `503`  | `demo_cache.json` not found or invalid JSON |

---

### `GET /api/demo/answer/{index}`

Returns the full pre-cached response for the question at position `index`
(0-based). Response schema is identical to `POST /api/query`.

**Path Parameters**

| Parameter | Type  | Description              |
|-----------|-------|--------------------------|
| `index`   | `int` | 0-based question index   |

**Response (200 OK)**

```json
{
  "question": "Why did we choose Neo4j over PostgreSQL?",
  "answer": "The team selected Neo4j ...",
  "citations": [
    {
      "id": "local_arch_decision_neo4j",
      "title": "Architecture Decision — Neo4j vs PostgreSQL",
      "source": "local",
      "author": "Sailesh Balaji",
      "timestamp": "2026-06-05T14:00:00+00:00",
      "url": ""
    }
  ],
  "plan": {
    "search_type": "hybrid",
    "sub_queries": ["..."],
    "entities": ["Neo4j", "PostgreSQL"],
    "topics": ["database selection"]
  },
  "elapsed_seconds": 8.4,
  "chunks_used": [],
  "_cached": true
}
```

**Error Responses**

| Status | Condition                          |
|--------|------------------------------------|
| `404`  | `index` is out of range (0–4)      |
| `503`  | Cache file unavailable at startup   |

---

## The 5 Canonical Demo Questions

| Index | Question | Search Type | Demo Purpose |
|-------|----------|-------------|--------------|
| 0 | Why did we choose Neo4j over PostgreSQL? | hybrid | Cross-source decision tracing |
| 1 | What has Sailesh been working on this week? | graph | Person-centric graph traversal |
| 2 | Show me the timeline of the authentication decision | hybrid | Chronological decision chain |
| 3 | What's the status of the frontend? | hybrid | Status/progress query |
| 4 | Who decided to use Qdrant and why? | hybrid | Gap detection (unanswerable) |

---

## Frontend Integration

The frontend can use this endpoint to populate the **Demo Mode** button or
a pre-built question chip list. Since `_cached: true` is present, the UI
may optionally display a "⚡ Demo answer" badge instead of a spinner.

```javascript
// Example: load questions on mount
const { data } = await fetch('/api/demo/questions').then(r => r.json());
// Click handler: get cached answer by index
const answer = await fetch(`/api/demo/answer/${index}`).then(r => r.json());
```

---

## File Layout

```
backend/
├── app/
│   └── api/
│       ├── demo.py              # This router (NEW)
│       └── specs/
│           └── demo_api.md      # This document (NEW)
└── data/
    └── demo_cache.json          # Pre-cached responses (NEW)
```
