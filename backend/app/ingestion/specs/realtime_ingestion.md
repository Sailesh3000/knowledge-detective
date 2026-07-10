# Real-Time Ingestion Architecture (Local-Only)

> How Knowledge Detective keeps its knowledge graph and vector store continuously up-to-date
> as local files change in monitored folders.

---

## Overview

The bulk test pipeline (`test_pipeline.py`) demonstrates a one-shot batch ingestion.
To react to live events in the local filesystem without requiring the user to manually re-run anything, the system uses a local file watcher daemon.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                        │
│                                                             │
│  ┌─────────────────────────────┐                           │
│  │   Local Filesystem Watcher  │ (watchdog, background)     │
│  │   Monitors: test-data/      │                           │
│  │   Events: create/modify/del │                           │
│  └──────────────┬──────────────┘                           │
│                 │                                           │
│                 ▼                                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Ingestion Pipeline                       │  │
│  │  Document → Chunk → Embed → LLM Extract → Graph      │  │
│  └──────────────────────┬────────────────────────────────┘  │
│                         │                                   │
│          ┌──────────────┼──────────────┐                    │
│          ▼              ▼              ▼                    │
│     ┌─────────┐   ┌──────────┐   ┌──────────┐             │
│     │  Qdrant │   │  Neo4j   │   │  Ollama  │             │
│     │ Vectors │   │  Graph   │   │  (LLM)   │             │
│     └─────────┘   └──────────┘   └──────────┘             │
└─────────────────────────────────────────────────────────────┘
```

---

## Local Filesystem Watcher

**Mechanism**: `watchdog` library — OS-level file system event monitoring.

**How it works**:
- The `LocalFolderWatcher` (in `watcher.py`) starts a background thread via `watchdog.Observer`.
- It monitors a configured folder (e.g., `test-data/`) recursively.
- On file **create** or **modify** (`.md`, `.txt`, `.pdf`): the file is parsed into a `Document` and pushed through the `IngestionPipeline`.
- On file **delete**: the corresponding document is removed from both Qdrant and Neo4j using the hashed document ID.

**Latency**: Near-instant (~500ms debounce to avoid partial-write triggers).

**Activation**: The watcher starts automatically when the FastAPI server boots:
```python
# In main.py (startup event)
@app.on_event("startup")
async def startup():
    watcher = LocalFolderWatcher()
    watcher.start("test-data/")
```

---

## Deduplication Strategy

Every document has a deterministic `id` derived from its source:

| Source   | ID Format                                         | Example                              |
|----------|---------------------------------------------------|--------------------------------------|
| Local    | `local_{md5(absolute_path)}`                      | `local_3db36ac0d3d5a19d...`          |

Before ingesting, the pipeline always calls `delete_document(doc_id)` first, which removes old vectors from Qdrant and old nodes/edges from Neo4j. This ensures that re-ingesting the same document (e.g. an edited document or note) produces a clean, up-to-date representation without duplicates.

---

## Error Handling & Resilience

| Scenario                        | Behavior                                                    |
|---------------------------------|-------------------------------------------------------------|
| Ollama offline                  | Metadata extraction is skipped; document still indexed in Qdrant and Neo4j with basic author/source info |
| Neo4j connection lost           | Pipeline returns `False`; document is retried on next write |
| Qdrant unreachable              | Pipeline returns `False`; document is retried on next write |
| Malformed LLM JSON response     | Caught by `json.JSONDecodeError`; empty metadata used       |

---

## Configuration (Environment Variables)

| Variable                          | Default                   | Description                                                    |
|-----------------------------------|---------------------------|----------------------------------------------------------------|
| `WATCH_DIRECTORY`                 | `test-data/`              | Local folder to monitor for changes                            |
| `OLLAMA_MODEL`                    | `qwen3:8b`               | LLM model used for entity extraction                           |
