# Knowledge Detective — Local-First Implementation Plan (v2)

## Problem Statement

Build an AI-powered system that **connects and reasons over fragmented information** across disparate sources (GitHub, Gmail, Google Calendar/Meet, local documents), providing:

1. **Q&A with Citations** — answers grounded in evidence, never fabricated
2. **Decision Timelines** — chronological reconstruction of how decisions evolved
3. **Knowledge Graph Visualization** — interactive map of people, docs, and relationships
4. **Gap Detection** — explicit identification of missing information

---

## Key Decisions (From User Feedback)

| Decision | Choice |
|----------|--------|
| **LLM** | `qwen3:8b` via Ollama (already installed, 5.2 GB) |
| **Test Data** | Synthetic data (fake emails, meeting notes, GitHub issues) simulating a real team building this project |
| **GitHub Repo** | Create a dedicated repo for this project to test against |
| **Gmail & Calendar** | Include in Phase 1 (not deferred) |
| **Embeddings** | `all-MiniLM-L6-v2` via sentence-transformers on CPU |

---

## Local Development Stack

| Component | Tool | Port | Cost |
|-----------|------|------|------|
| **LLM Inference** | Ollama (`qwen3:8b`) | `localhost:11434` | Free |
| **Embeddings** | sentence-transformers CPU | In-process | Free |
| **Graph DB** | Neo4j Community (Docker) | `:7474` (browser), `:7687` (bolt) | Free |
| **Vector DB** | Qdrant (Docker) | `:6333` (REST), `:6334` (gRPC) | Free |
| **Backend** | FastAPI (Python) | `:8000` | Free |
| **Frontend** | React + Vite | `:5173` | Free |

> **Cloud migration later is trivial**: Ollama exposes an OpenAI-compatible API at `localhost:11434/v1`. When GPU credits arrive, swap the base URL to Fireworks AI — zero code changes in the agent logic.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Your Windows Machine                      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │   Neo4j       │  │   Qdrant     │  │  Ollama (qwen3:8b) │  │
│  │   (Docker)    │  │   (Docker)   │  │  localhost:11434    │  │
│  │  :7474/:7687  │  │  :6333/:6334 │  │  (already running) │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘  │
│         │                  │                    │              │
│  ┌──────┴──────────────────┴────────────────────┴───────────┐ │
│  │               Backend (FastAPI) :8000                      │ │
│  │                                                            │ │
│  │  INGESTION LAYER                                           │ │
│  │  ┌────────┐ ┌───────┐ ┌──────────┐ ┌───────────────────┐ │ │
│  │  │ GitHub │ │ Gmail │ │ Calendar │ │ Local Folders      │ │ │
│  │  └───┬────┘ └───┬───┘ └────┬─────┘ └────────┬──────────┘ │ │
│  │      └──────────┴──────────┴─────────────────┘            │ │
│  │                         ↓                                  │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │ Pipeline: Extract → Chunk → Embed → Build Graph     │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  │                                                            │ │
│  │  QUERY LAYER                                               │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ Plan → Retrieve (Vector+Graph) → Verify → Synthesize │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────┬───────────────────────────────┘ │
│                               │                                │
│  ┌────────────────────────────┴──────────────────────────────┐ │
│  │               Frontend (React + Vite) :5173                │ │
│  │  ┌──────────┐  ┌────────────────┐  ┌───────────────────┐ │ │
│  │  │ Chat UI  │  │ Timeline View  │  │ Graph Viz         │ │ │
│  │  │ (Q&A +   │  │ (Decisions by  │  │ (react-force-     │ │ │
│  │  │ Sources) │  │  time)         │  │  graph)           │ │ │
│  │  └──────────┘  └────────────────┘  └───────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

---

## Ingestion Flow (How Data Gets In)

Understanding this is critical — ingestion is what makes the system work.

### Why Not Just Query Live?

| Without Ingestion (Bad) | With Ingestion (Good) |
|-------------------------|----------------------|
| Every query hits GitHub API, Gmail API, etc. live → **slow** (seconds per source) | Data is pre-indexed → **instant** retrieval |
| Can't do semantic search ("find things related to auth") without pre-computed embeddings | Embeddings pre-computed → semantic search in milliseconds |
| Can't traverse cross-source relationships without a pre-built graph | Knowledge graph pre-built → "who discussed this PR?" is a single Cypher query |
| API rate limits would kill you on repeated queries | Ingested once, queried unlimited times |

### How It Works

```
BULK INGESTION (first time — runs once)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Source APIs          Extract           Chunk            Embed              Store
┌──────────┐     ┌──────────────┐   ┌───────────┐   ┌──────────────┐   ┌────────────┐
│ GitHub   │────→│ Pull issues, │──→│ Split into│──→│ all-MiniLM   │──→│ Qdrant     │
│ Gmail    │     │ PRs, emails, │   │ ~500 token│   │ -L6-v2       │   │ (vectors)  │
│ Calendar │     │ meetings,    │   │ chunks w/ │   │ CPU encoding │   ├────────────┤
│ Local    │     │ local docs   │   │ overlap   │   └──────────────┘   │ Neo4j      │
└──────────┘     └──────────────┘   └───────────┘                      │ (graph)    │
                       ↓                                                └────────────┘
                 ┌──────────────┐
                 │ LLM Metadata │  → Extract entities, topics, people
                 │ Extraction   │  → Resolve identities (email ↔ github ↔ name)
                 │ (qwen3:8b)   │  → Create AUTHORED_BY, MENTIONS, REFERENCES edges
                 └──────────────┘

INCREMENTAL SYNC (ongoing — for real-time use)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Only NEW/MODIFIED items get processed.
→ GitHub: webhooks or poll for new issues/PRs since last sync
→ Gmail: push notifications or poll for new emails since last sync
→ Calendar: watch for new/updated events
→ Local: file watcher detects changes
```

### For Another Project

A new user would:
1. **Open the Settings UI** → connect their GitHub repos, Gmail, Calendar
2. **Click "Ingest"** → bulk import runs (minutes for a typical project)
3. **Start asking questions** → the system searches the pre-built index + graph
4. **Auto-sync** keeps data fresh going forward

---

## Test Data Strategy

Since we're creating a repo for this project, we'll generate **synthetic but realistic** data that simulates a team building Knowledge Detective:

### Synthetic Data Set

| Source | Contents | Count |
|--------|----------|-------|
| **GitHub Issues** | Feature requests, bug reports, design discussions about the project | ~15-20 issues |
| **GitHub PRs** | Implementation PRs linked to issues, with review comments | ~10-15 PRs |
| **Emails** | Team discussions about architecture decisions, deadline negotiations, questions | ~20-25 emails |
| **Meeting Notes** | Sprint planning, design reviews, retrospectives (as `.md` files simulating transcripts) | ~8-10 meetings |
| **Local Docs** | The build plan, architecture docs, API specs, decision records | ~5-10 docs |

### Cross-Source Links (What Makes It Interesting)

- Email from `sailesh@example.com` discusses "we should use Neo4j" → Meeting notes from the same day reference the same decision → GitHub Issue #5 is created as a result → PR #8 implements it
- This creates a traceable **decision chain** across email → meeting → issue → PR

### Pre-Built Demo Queries

| Query | Expected Behavior |
|-------|-------------------|
| "Why did we choose Neo4j over PostgreSQL?" | Finds the email discussion + meeting notes + decision doc, cites all three |
| "What has Sailesh been working on this week?" | Traverses `Person → AUTHORED_BY → PR/Issue/Email` edges |
| "Show me the timeline of the authentication decision" | Returns chronological chain: email → meeting → issue → PR |
| "What's the status of the frontend?" | Finds relevant issues/PRs, identifies open items |
| "Who decided to use Qdrant?" | *If no evidence exists*, system says "No decision record found for Qdrant selection" instead of guessing |

---

## Project File Structure

```
knowledge-detective/
├── knowledge-detective-build-plan.md    # Existing
├── implementation-plan.md               # This file
├── docker-compose.yml                   # Neo4j + Qdrant
├── .env.example                         # Template for env vars
├── .gitignore
│
├── backend/
│   ├── requirements.txt
│   ├── .env                             # Local config (git-ignored)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI entry point + CORS
│   │   ├── config.py                    # Settings (Ollama URL, DB URLs, model name)
│   │   │
│   │   ├── models/                      # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── document.py              # Document, Chunk, Entity, Source enums
│   │   │   └── query.py                 # QueryRequest, SubQuery, Evidence, Answer
│   │   │
│   │   ├── connectors/                  # Data source connectors
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # AbstractConnector interface
│   │   │   ├── github_connector.py      # GitHub REST API
│   │   │   ├── gmail_connector.py       # Gmail API + OAuth
│   │   │   ├── calendar_connector.py    # Google Calendar API + OAuth
│   │   │   └── local_connector.py       # Local file scanner
│   │   │
│   │   ├── ingestion/                   # Processing pipeline
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py              # Orchestrates the full flow
│   │   │   ├── chunker.py               # Text splitting strategies
│   │   │   ├── embedder.py              # sentence-transformers (CPU)
│   │   │   ├── metadata_extractor.py    # LLM-based entity/topic extraction
│   │   │   └── graph_builder.py         # Neo4j node + edge creation
│   │   │
│   │   ├── retrieval/                   # Query-time retrieval
│   │   │   ├── __init__.py
│   │   │   ├── vector_search.py         # Qdrant similarity search
│   │   │   ├── graph_search.py          # Neo4j Cypher traversals
│   │   │   └── hybrid.py               # Merges vector + graph results
│   │   │
│   │   ├── agent/                       # LLM reasoning agent
│   │   │   ├── __init__.py
│   │   │   ├── llm_client.py            # Ollama/OpenAI-compatible client
│   │   │   ├── planner.py               # Decomposes questions → sub-queries
│   │   │   ├── verifier.py              # Evidence validation, anti-hallucination
│   │   │   └── synthesizer.py           # Cited answer generation
│   │   │
│   │   └── api/                         # FastAPI route handlers
│   │       ├── __init__.py
│   │       ├── ingest.py                # POST /api/ingest/{source}
│   │       ├── query.py                 # POST /api/query
│   │       ├── timeline.py              # GET /api/timeline/{topic}
│   │       └── graph.py                 # GET /api/graph/{entity}
│   │
│   ├── scripts/
│   │   ├── generate_test_data.py        # Creates synthetic emails, meetings, issues
│   │   └── smoke_test.py               # Verifies full pipeline works
│   │
│   └── tests/
│       ├── test_connectors.py
│       ├── test_ingestion.py
│       └── test_agent.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css                    # Design system (dark mode, glassmorphism)
│       ├── api/
│       │   └── client.js               # Backend API wrapper
│       └── components/
│           ├── Layout.jsx               # App shell + navigation
│           ├── ChatPanel.jsx            # Q&A chat interface
│           ├── SourceCard.jsx           # Evidence/citation card
│           ├── Timeline.jsx             # Decision timeline view
│           ├── GraphViz.jsx             # Knowledge graph (react-force-graph)
│           ├── IngestionPanel.jsx       # Source connection + ingest controls
│           └── SettingsPanel.jsx        # API keys, repo URLs, OAuth config
│
└── test-data/                           # Synthetic test corpus
    ├── emails/                          # Fake email threads (.json)
    ├── meetings/                        # Meeting notes (.md)
    ├── docs/                            # Architecture docs, decision records
    └── README.md                        # Describes the test data set
```

---

## Phase Breakdown

### Phase 1: Foundation (Scaffolding + Infrastructure + ALL Connectors)
**Goal**: Project skeleton running, all 4 connectors built, databases up.

1. Create `docker-compose.yml` → `docker compose up -d` (Neo4j + Qdrant)
2. Scaffold FastAPI backend with config pointing to Ollama `qwen3:8b`
3. Build all 4 connectors:
   - **GitHub**: PyGithub, pulls issues/PRs/commits
   - **Gmail**: Google Gmail API + OAuth2 desktop flow
   - **Calendar**: Google Calendar API + OAuth2 (shared credentials with Gmail)
   - **Local Folders**: Scans `.md`, `.txt`, `.pdf` files
4. Generate synthetic test data (`scripts/generate_test_data.py`)
5. Create GitHub repo for the project, push initial issues/PRs

### Phase 2: Ingestion Pipeline + Knowledge Graph
**Goal**: Data flows from connectors → chunks → embeddings → graph.

1. Text chunker (500 tokens, 50 token overlap)
2. Embedder (`all-MiniLM-L6-v2` on CPU → Qdrant)
3. LLM metadata extraction (qwen3:8b extracts entities, topics, people)
4. Graph builder (Neo4j nodes + edges + identity resolution)
5. Run bulk ingestion on test data, verify in Neo4j Browser + Qdrant Dashboard
6. Background local file watcher daemon (`watchdog` listening to changes and incrementally updating Qdrant/Neo4j)

### Phase 3: Query Engine + Reasoning Agent
**Goal**: Ask a question → get a cited answer.

1. LLM client wrapper (Ollama OpenAI-compatible endpoint)
2. Planner (decompose question → sub-queries + search strategy)
3. Hybrid retriever (vector search + graph traversal)
4. Verifier (validate evidence, reject hallucinations)
5. Synthesizer (produce cited answer)
6. Wire up API routes: `/api/query`, `/api/timeline/{topic}`, `/api/graph/{entity}`

### Phase 4: Frontend UI
**Goal**: Premium dark-mode interface with Chat, Timeline, and Graph views.

1. Scaffold React + Vite app
2. Design system (dark mode, glassmorphism, Inter font, accent colors)
3. Chat Panel with streaming responses + inline citations
4. Decision Timeline (vertical, date-sorted, filterable by source)
5. Knowledge Graph Viz (react-force-graph-2d, color-coded nodes, 1-2 hop)
6. Ingestion/Settings panel (connect sources, trigger ingestion)

---

## Google OAuth Setup (For Gmail & Calendar)

Since we're including Gmail & Calendar in Phase 1, here's the OAuth plan:

1. Create a **Google Cloud Project** at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable **Gmail API** and **Google Calendar API**
3. Create **OAuth 2.0 Desktop Application** credentials
4. Download `credentials.json` → place in `backend/`
5. First run triggers browser-based consent flow → saves `token.json` for reuse

> **Note**: Since this is a development/demo app, we'll use "Testing" mode in GCP (allows up to 100 test users without verification). No need for a published app.

---

## Verification Plan

### Automated Tests
```bash
# Backend unit tests
cd backend && pytest tests/ -v

# Ingestion smoke test
python -m scripts.smoke_test

# Query pipeline test — 5 predefined questions
python -m scripts.query_test
```

### Manual Verification
- **Neo4j Browser** (`http://localhost:7474`) → `MATCH (n) RETURN n LIMIT 50` → see graph
- **Qdrant Dashboard** (`http://localhost:6333/dashboard`) → verify collections + counts
- **Demo query 1**: "Why did we choose Neo4j?" → expect cited answer from emails + meeting notes
- **Demo query 2**: "What has Sailesh worked on?" → expect person-centric graph traversal
- **Demo query 3**: "What's the status of payments integration?" → expect "no evidence found" (gap detection)
- **Timeline view**: Search "authentication" → expect chronological decision chain
- **Graph view**: Click "Sailesh" → see connected PRs, issues, emails, meetings

---

## Execution Order Summary

| Step | What | Est. Time |
|------|------|-----------|
| 1 | `docker-compose.yml` + FastAPI skeleton + config | ~45 min |
| 2 | All 4 connectors (GitHub, Gmail, Calendar, Local) | ~3 hours |
| 3 | Generate synthetic test data + create GitHub repo | ~1 hour |
| 4 | Ingestion pipeline (chunk → embed → extract → graph) + Watcher | ~3 hours |
| 5 | Ingest test data, verify in Neo4j/Qdrant | ~30 min |
| 6 | Query engine (plan → retrieve → verify → synthesize) | ~3 hours |
| 7 | API routes (query, timeline, graph) | ~1 hour |
| 8 | React frontend (Chat + Timeline + Graph Viz) | ~3-4 hours |
| 9 | Polish, testing, demo prep | ~1 hour |
| | **Total** | **~16.5 hours** |
