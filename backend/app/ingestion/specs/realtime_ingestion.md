# Real-Time Ingestion Architecture

> How Knowledge Detective keeps its knowledge graph and vector store continuously up-to-date
> as new emails arrive, meetings happen, commits land, and local files change.

---

## Overview

The bulk test pipeline (`test_pipeline.py`) demonstrates a one-shot batch ingestion.
In production, the system must react to **live events** from four sources — Gmail, Google Calendar, GitHub, and the local filesystem — without requiring the user to manually re-run anything.

This document specifies the real-time ingestion strategy for each source.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                        │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Sync Scheduler (APScheduler)             │  │
│  │                                                       │  │
│  │  ┌─────────┐  ┌──────────┐  ┌───────────────────┐    │  │
│  │  │  Gmail   │  │ Calendar │  │     GitHub         │    │  │
│  │  │  Poller  │  │  Poller  │  │  Webhook Receiver  │    │  │
│  │  │ (5 min)  │  │ (15 min) │  │  (push events)     │    │  │
│  │  └────┬─────┘  └────┬─────┘  └────────┬──────────┘    │  │
│  └───────┼──────────────┼────────────────┼───────────────┘  │
│          │              │                │                   │
│          ▼              ▼                ▼                   │
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

  ┌─────────────────────────────┐
  │   Local Filesystem Watcher  │  (watchdog, always-on daemon)
  │   Monitors: test-data/      │
  │   Events: create/modify/del │
  └──────────────┬──────────────┘
                 │
                 ▼
          Ingestion Pipeline
```

---

## Source-by-Source Strategy

### 1. Local Filesystem (Already Implemented ✅)

**Mechanism**: `watchdog` library — OS-level file system event monitoring.

**How it works**:
- The `LocalFolderWatcher` (in `watcher.py`) starts a background thread via `watchdog.Observer`.
- It monitors a configured folder (e.g. `test-data/`) recursively.
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

### 2. Gmail (Polling with Incremental Sync)

**Mechanism**: Scheduled polling via `APScheduler` using the Gmail API's `historyId` for incremental sync.

**Project Relevance Filter**: Gmail API supports a query string (same syntax as the Gmail search bar). The poller uses `GMAIL_QUERY` to restrict which emails are synced. Examples:

```bash
# .env — Only sync emails involving the project team or matching project keywords
GMAIL_QUERY='subject:"knowledge-detective" OR subject:"KD" OR from:tejas@example.com OR from:abhilash@example.com'
```

Alternatively, create a Gmail **label** (e.g. `knowledge-detective`) and set up a Gmail filter rule to auto-label incoming project emails:
```bash
GMAIL_QUERY='label:knowledge-detective'
```

**How it works**:
1. On first run, `GmailConnector.fetch_documents(query=GMAIL_QUERY)` pulls matching emails and stores the most recent `historyId` in a local state file (`backend/state/gmail_state.json`).
2. On subsequent polls (every 5 minutes), the system calls `users().history().list(startHistoryId=last_known_id)` to fetch **only new or changed messages** since the last sync, then re-applies the query filter to ensure relevance.
3. Each new/modified message is converted to a `Document` and pushed through `IngestionPipeline.ingest_document()`.
4. Deleted messages trigger `IngestionPipeline.delete_document()`.

**State file format** (`gmail_state.json`):
```json
{
  "last_history_id": "1234567",
  "last_sync_at": "2026-07-09T12:00:00Z",
  "query": "label:knowledge-detective"
}
```

**Why polling and not push?**
Gmail push notifications require a public HTTPS endpoint with a valid domain + SSL certificate for Pub/Sub. For a local-first tool, scheduled polling with incremental `historyId` sync is simpler, reliable, and avoids cloud infrastructure dependencies.

**Poll interval**: Every **5 minutes** (configurable via `GMAIL_POLL_INTERVAL_SECONDS` env var).

---

### 3. Google Calendar (Polling with syncToken)

**Mechanism**: Scheduled polling via `APScheduler` using the Calendar API's `syncToken` for incremental sync.

**Project Relevance Filter**: Calendar events are filtered using two strategies:

**Strategy A — Dedicated Project Calendar (Recommended)**:
Create a shared Google Calendar named "Knowledge Detective" for all project meetings. Configure the system to sync only that calendar:
```bash
# .env — Calendar ID of the project-specific calendar
CALENDAR_ID='abc123xyz@group.calendar.google.com'
```

**Strategy B — Attendee-Based Filtering**:
If using the primary calendar, filter events post-fetch by checking if any project team member is in the attendee list:
```bash
# .env — Comma-separated project team email addresses
PROJECT_TEAM_EMAILS='sailesh@example.com,tejas@example.com,abhilash@example.com'
```
The poller will discard events where none of the project team members are attendees.

**Strategy C — Keyword Filtering**:
Filter events by title keywords:
```bash
# .env — Comma-separated keywords that must appear in the event title
CALENDAR_KEYWORDS='knowledge-detective,KD,sprint,standup,retro'
```

**How it works**:
1. On first run, `CalendarConnector.fetch_documents()` pulls events from the configured calendar (or primary calendar with filters). The API response includes a `nextSyncToken`.
2. The `nextSyncToken` is saved to `backend/state/calendar_state.json`.
3. On subsequent polls (every 15 minutes), the system calls `events().list(syncToken=saved_token)` which returns **only events that changed** since the last sync (new, updated, or cancelled).
4. Each event passes through the relevance filter (attendee check or keyword match) before ingestion.
5. New/updated relevant events are ingested; cancelled events trigger document deletion.

**State file format** (`calendar_state.json`):
```json
{
  "sync_token": "CPDAlvDi8eoCEPDAlvDi8eoC",
  "last_sync_at": "2026-07-09T12:00:00Z",
  "calendar_id": "abc123xyz@group.calendar.google.com"
}
```

**Poll interval**: Every **15 minutes** (configurable via `CALENDAR_POLL_INTERVAL_SECONDS` env var).

---

### 4. GitHub (Webhook-Driven, Real-Time Push)

**Mechanism**: GitHub Webhook → FastAPI POST endpoint → Ingestion Pipeline.

**How it works**:
1. A webhook is configured on the GitHub repository (e.g. `Sailesh3000/knowledge-detective`) to send `push`, `issues`, `pull_request`, and `issue_comment` events to `POST /api/webhooks/github`.
2. The FastAPI endpoint receives the JSON payload, validates the `X-Hub-Signature-256` header using a shared secret, and parses it into one or more `Document` objects.
3. Each document is pushed through `IngestionPipeline.ingest_document()`.

**Supported event types**:

| GitHub Event       | What gets ingested                        |
|--------------------|-------------------------------------------|
| `push`             | Each commit message + changed file list   |
| `issues`           | Issue title + body + labels               |
| `pull_request`     | PR title + body + diff summary            |
| `issue_comment`    | Comment body linked to parent issue/PR    |

**Webhook endpoint**:
```python
@app.post("/api/webhooks/github")
async def github_webhook(request: Request):
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event")
    # Validate signature, parse payload, ingest documents
```

**For local development** (no public URL): Use a polling fallback:
- `APScheduler` polls `GitHubConnector.fetch_documents()` every **10 minutes** using the `since` parameter to fetch only new items.
- State is tracked in `backend/state/github_state.json`:
  ```json
  {
    "last_checked_at": "2026-07-09T12:00:00Z"
  }
  ```

---

## Deduplication Strategy

Every document has a deterministic `id` derived from its source:

| Source   | ID Format                                         | Example                              |
|----------|---------------------------------------------------|--------------------------------------|
| Gmail    | `gmail_{message_id}`                              | `gmail_msg_001`                      |
| Calendar | `calendar_{event_id}`                             | `calendar_abc123`                    |
| GitHub   | `github_{type}_{repo}_{number_or_sha}`            | `github_issue_knowledge-detective_5` |
| Local    | `local_{md5(absolute_path)}`                      | `local_3db36ac0d3d5a19d...`          |

Before ingesting, the pipeline always calls `delete_document(doc_id)` first, which removes old vectors from Qdrant and old nodes/edges from Neo4j. This ensures that re-ingesting the same document (e.g. an edited email draft or updated issue) produces a clean, up-to-date representation without duplicates.

---

## Sync Scheduler Implementation

The scheduler is implemented using `APScheduler` (Advanced Python Scheduler), integrated with FastAPI's lifespan:

```python
# backend/app/sync_scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(sync_gmail,    "interval", minutes=5,  id="gmail_sync")
    scheduler.add_job(sync_calendar, "interval", minutes=15, id="calendar_sync")
    scheduler.add_job(sync_github,   "interval", minutes=10, id="github_sync")
    scheduler.start()

async def sync_gmail():
    """Incremental Gmail sync using historyId."""
    connector = GmailConnector()
    pipeline = IngestionPipeline()
    state = load_state("gmail_state.json")
    # ... fetch only new messages since last_history_id
    # ... ingest each new message
    # ... save updated history_id

async def sync_calendar():
    """Incremental Calendar sync using syncToken."""
    # Similar pattern with syncToken

async def sync_github():
    """Polling fallback for GitHub when webhooks aren't available."""
    # Similar pattern with since timestamp
```

**Startup integration** (in `main.py`):
```python
@app.on_event("startup")
async def startup():
    # 1. Start local file watcher
    watcher = LocalFolderWatcher()
    watcher.start("test-data/")

    # 2. Start scheduled sync jobs
    start_scheduler()
```

---

## State Management

All sync state is persisted in `backend/state/` as JSON files:

```
backend/state/
├── gmail_state.json       # { last_history_id, last_sync_at }
├── calendar_state.json    # { sync_token, last_sync_at }
└── github_state.json      # { last_checked_at }
```

State files are `.gitignore`-d since they contain user-specific sync cursors.

---

## Error Handling & Resilience

| Scenario                        | Behavior                                                    |
|---------------------------------|-------------------------------------------------------------|
| Ollama offline                  | Metadata extraction is skipped; document still indexed in Qdrant and Neo4j with basic author/source info |
| Gmail API quota exceeded        | Scheduler retries on the next interval; logs a warning      |
| Neo4j connection lost           | Pipeline returns `False`; document is retried on next sync  |
| Qdrant unreachable              | Pipeline returns `False`; document is retried on next sync  |
| Malformed LLM JSON response     | Caught by `json.JSONDecodeError`; empty metadata used       |
| Duplicate webhook delivery      | Idempotent — `delete_document()` runs before every ingest   |

---

## Configuration (Environment Variables)

| Variable                          | Default                   | Description                                                    |
|-----------------------------------|---------------------------|----------------------------------------------------------------|
| `GMAIL_POLL_INTERVAL_SECONDS`     | `300` (5 min)             | How often to check for new emails                              |
| `GMAIL_QUERY`                     | `""`                      | Gmail search query to filter project-relevant emails           |
| `CALENDAR_POLL_INTERVAL_SECONDS`  | `900` (15 min)            | How often to check for new events                              |
| `CALENDAR_ID`                     | `primary`                 | Google Calendar ID to sync (use a project-specific calendar)   |
| `PROJECT_TEAM_EMAILS`             | `""`                      | Comma-separated team emails for calendar attendee filtering    |
| `CALENDAR_KEYWORDS`               | `""`                      | Comma-separated keywords to match in calendar event titles     |
| `GITHUB_POLL_INTERVAL_SECONDS`    | `600` (10 min)            | Polling fallback interval for GitHub                           |
| `GITHUB_WEBHOOK_SECRET`           | (none)                    | Shared secret for webhook validation                           |
| `WATCH_DIRECTORY`                 | `test-data/`              | Local folder to monitor for changes                            |
| `OLLAMA_MODEL`                    | `qwen3:8b`               | LLM model used for entity extraction                           |
