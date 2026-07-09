import os
import json
from datetime import datetime, timedelta, timezone

# Output directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "test-data"))
EMAILS_DIR = os.path.join(TEST_DATA_DIR, "emails")
MEETINGS_DIR = os.path.join(TEST_DATA_DIR, "meetings")
DOCS_DIR = os.path.join(TEST_DATA_DIR, "docs")

def ensure_dirs():
    for d in [EMAILS_DIR, MEETINGS_DIR, DOCS_DIR]:
        os.makedirs(d, exist_ok=True)

def generate_docs():
    """
    Generate 6 architectural and requirement documents.
    """
    docs = {
        "product_requirements.md": """# Product Requirements Document (PRD): Knowledge Detective

**Author:** Tejas (Product & Frontend)
**Date:** 2026-06-03
**Status:** Approved

## 1. Overview
Knowledge Detective is an AI-powered system designed to run locally on a developer's machine. Its primary objective is to connect, index, and reason over highly fragmented project knowledge across Google Workspace (Gmail/Calendar), GitHub repos, and local documentation folders.

## 2. Core Features
1. **Semantic Search & Q&A**: Hybrid query answering using vector search and Graph DB traversals with strict source citation.
2. **Decision Timelines**: Interactive chronological visualizer showing how a decision evolved across emails, meetings, and code commits.
3. **Interactive Knowledge Graph**: Graph rendering representing connections between people, topics, code artifacts, and emails.
4. **Information Gap Detection**: Flags questions that cannot be answered by the current index and logs them as gaps.

## 3. High-Level Requirements
* **Local First**: Keep database running in local Docker containers (Neo4j & Qdrant) and inference local using Ollama (`qwen3:8b`).
* **Privacy**: Code base, tokens, and data should never leave the local machine.
""",
        "ADR-001-graph-database.md": """# Architecture Decision Record (ADR) 001: Graph Database Selection

**Author:** Sailesh (Lead Architect)
**Date:** 2026-06-10
**Status:** Accepted

## Context
Our application needs to trace indirect connections across different data sources (e.g., "Find the developer who discussed this PR in a meeting"). Doing multi-hop traversals in a standard SQL database requires complex recursive JOINs, which are difficult to write, maintain, and execute efficiently.

## Decision
We will use **Neo4j Community Edition** (deployed via Docker) as our Graph Database. 

## Alternatives Considered
1. **PostgreSQL with recursive CTEs**: Rejected due to high maintenance overhead and complexity in updating relationships dynamically.
2. **Apache Age (PostgreSQL Graph extension)**: Rejected due to complex setup and lack of native Python ecosystem libraries relative to Neo4j.

## Consequences
* We must run a Neo4j Docker container on port `7474` (browser) and `7687` (bolt).
* We will use Cypher queries to build and traverse relationships like `(Person)-[:AUTHORED]->(Document)`.
""",
        "ADR-002-vector-database.md": """# Architecture Decision Record (ADR) 002: Vector Database Selection

**Author:** Sailesh (Lead Architect)
**Date:** 2026-06-14
**Status:** Accepted

## Context
For semantic search and text matching, we need a vector database to store and query dense vector embeddings (`all-MiniLM-L6-v2`) generated from text chunks.

## Decision
We will use **Qdrant** (deployed via Docker) as our vector database.

## Alternatives Considered
1. **pgvector (PostgreSQL)**: Rejected. While convenient, running dedicated vector indexing like HNSW in Postgres inside lightweight containers consumes more memory and is slower to scaffold than Qdrant.
2. **Chroma**: Rejected. Chroma is great for Python-only quick starts, but lacks a robust standalone web dashboard for inspecting index contents, which is critical for development visibility.

## Consequences
* We will deploy Qdrant on port `6333` (REST).
* Chunks will be stored with payload metadata including document ID, source type, and author.
""",
        "ADR-003-google-oauth.md": """# Architecture Decision Record (ADR) 003: Google OAuth for Headless/Docker Development

**Author:** Abhilash (Security & Infra)
**Date:** 2026-06-21
**Status:** Accepted

## Context
Our backend runs inside a headless Docker container. Google's standard OAuth helper (`InstalledAppFlow`) assumes a browser is available locally on the machine running the code to complete the OAuth consent page redirect.

## Decision
We will override `google_auth_oauthlib`'s flow by writing a custom WSGI server inside the container that:
1. Registers `http://localhost:8080/` as the callback redirect (allowed by Google).
2. Binds the server socket to `0.0.0.0:8080` (enabling Docker's port mapping to forward the host browser's redirect request into the container).
3. Replaces `0.0.0.0` or raw container IPs in the callback response URI with `localhost` to satisfy local transport checks.
4. Uses `OAUTHLIB_INSECURE_TRANSPORT = 1` for local HTTP verification.

## Consequences
* Users must run Docker mapping `-p 8080:8080`.
* The `token.json` containing credentials will be cached in the mounted directory.
""",
        "frontend_architecture.md": """# Frontend Architecture Specification

**Author:** Tejas (Product & Frontend)
**Date:** 2026-06-30
**Status:** Approved

## 1. Stack Selection
* **Core**: React 18, Vite (for fast build times and HMR).
* **Styling**: Vanilla CSS with CSS Variables for theme design.
* **Graph Rendering**: `react-force-graph-2d` for interactive 2D physics-based force graphs.
* **Component Framework**: Custom glassmorphism layout to provide a premium dashboard aesthetic.

## 2. Views
1. **Dashboard Shell**: Navigation between Chat, Timeline, and Graph views.
2. **Chat Interface**: Standard QA layout with message lists. Citations are displayed as clickable cards that highlight in-context text.
3. **Timeline View**: A chronological timeline containing cards from all sources. Clicking a timeline node opens the source document in a modal.
4. **Graph Canvas**: Interactive node-link diagram. Clicking nodes triggers sidebar filters.
""",
        "api_endpoints.md": """# Backend API Endpoint Specifications

**Author:** Sailesh (Lead Architect)
**Date:** 2026-07-06
**Status:** Draft

This document outlines the API contracts for the backend server (`backend/app/main.py`).

## Endpoints

### 1. Ingestion Control
* **URL**: `/api/ingest/{source}`
* **Method**: `POST`
* **Description**: Triggers manual sync for a specific source (`github`, `gmail`, `calendar`, `local`).

### 2. Semantic Search & Q&A
* **URL**: `/api/query`
* **Method**: `POST`
* **Body**:
  ```json
  {
    "query": "Why did we choose Neo4j?",
    "filters": {
      "sources": ["gmail", "local"],
      "start_date": "2026-06-01T00:00:00Z"
    }
  }
  ```
* **Response**:
  ```json
  {
    "answer": "We chose Neo4j because...",
    "citations": [
      {
        "id": "doc_adr001",
        "title": "ADR 001: Graph Database Selection",
        "snippet": "We will use Neo4j Community Edition...",
        "confidence": 0.98
      }
    ]
  }
  ```
"""
    }

    for name, content in docs.items():
        with open(os.path.join(DOCS_DIR, name), "w", encoding="utf-8") as f:
            f.write(content.strip())
    print(f"Generated {len(docs)} documents in {DOCS_DIR}")

def generate_meetings():
    """
    Generate 8 meeting note/transcript markdown documents.
    """
    meetings = {
        "2026-06-01_kickoff_meeting.md": """# Meeting Notes: Kickoff Meeting
**Date:** 2026-06-01 10:00 UTC
**Attendees:** Sailesh, Tejas, Abhilash
**Topic:** Launching Knowledge Detective

## Discussion
* **Tejas** introduced the project goals. The product must solve internal information siloing.
* **Sailesh** suggested building the backend using FastAPI and Docker. He emphasized that local-first is essential because of data confidentiality.
* **Abhilash** brought up concerns about indexing credentials and suggested that tokens should be stored in `token.json` locally and git-ignored.
* **Tejas** asked about the frontend framework. He wants to build a unified interface showing Chat, Timelines, and a Graph.

## Action Items
* **Sailesh**: Scaffold backend and docker compose file (Due: Jun 5).
* **Abhilash**: Check OAuth scopes needed for Google Calendar and Gmail (Due: Jun 8).
* **Tejas**: Scaffold Vite template and design systems (Due: Jun 10).
""",
        "2026-06-08_architecture_review.md": """# Meeting Notes: Architecture Review
**Date:** 2026-06-08 14:00 UTC
**Attendees:** Sailesh, Abhilash, Tejas
**Topic:** Database selection - Neo4j vs relational DB

## Discussion
* **Sailesh** presented the case for a graph database: traversing indirect dependencies across emails and PRs is extremely slow in SQL databases. Neo4j allows writing simple Cypher queries to traverse these paths.
* **Abhilash** questioned if a graph database is too heavy. Sailesh explained we can run the Neo4j community edition inside a Docker container with low memory limits.
* **Tejas** loved the graph approach because `react-force-graph` consumes JSON structures with node/edge lists directly.
* **Abhilash** asked about vector storage. Sailesh said we will discuss vector databases in the next meeting.

## Action Items
* **Sailesh**: Write ADR-001 recommending Neo4j (Due: Jun 10).
""",
        "2026-06-13_database_decision_sync.md": """# Meeting Notes: Database Decision Sync
**Date:** 2026-06-13 11:00 UTC
**Attendees:** Sailesh, Abhilash
**Topic:** Vector Database - pgvector vs Qdrant

## Discussion
* **Sailesh** suggested pgvector since we are already using Postgres for other tasks.
* **Abhilash** countered: We don't have Postgres in the plan! Keeping it simple with Qdrant is better because Qdrant is lightweight, has a built-in search UI dashboard, and is optimized for CPU similarity search.
* **Sailesh** reviewed Qdrant's specs and agreed. Running Qdrant in Docker takes less than 50MB of RAM.

## Action Items
* **Sailesh**: Write ADR-002 recommending Qdrant and update `docker-compose.yml` (Due: Jun 15).
""",
        "2026-06-20_oauth_planning.md": """# Meeting Notes: OAuth and Security Planning
**Date:** 2026-06-20 09:30 UTC
**Attendees:** Abhilash, Sailesh
**Topic:** Google API Authentication in Docker

## Discussion
* **Abhilash** pointed out that running inside a headless Docker container makes standard Google auth flow crash since it tries to open a browser window on the container OS.
* **Sailesh** suggested using a static verification code copy-paste method.
* **Abhilash** noted that Google has officially deprecated Out-Of-Band (OOB) auth flow, so copy-paste codes are no longer supported.
* **Sailesh** proposed starting a temporary WSGI web server on port `8080` inside the container. We can expose that port in Docker, and the user's host browser will redirect to `localhost:8080`, which Docker forwards inside.

## Action Items
* **Abhilash**: Write ADR-003 and configure the GCP consent screen for testing (Due: Jun 22).
* **Sailesh**: Write the custom WSGI server inside `google_auth.py` (Due: Jun 25).
""",
        "2026-06-29_frontend_sync.md": """# Meeting Notes: Frontend Sync
**Date:** 2026-06-29 15:00 UTC
**Attendees:** Tejas, Sailesh, Abhilash
**Topic:** Scaffolding and Component Design

## Discussion
* **Tejas** showed a mockup of the glassmorphism layout. It includes a sidebar for navigation and a main workspace area.
* **Tejas** requested a vertical timeline view for tracking decision histories.
* **Sailesh** explained how he will structure the REST endpoints to feed the timeline: the backend will query Neo4j for entities and return them sorted by timestamp.

## Action Items
* **Tejas**: Scaffold Vite React app and build CSS stylesheet (Due: Jul 3).
""",
        "2026-07-02_sprint_1_retro.md": """# Meeting Notes: Sprint 1 Retro
**Date:** 2026-07-02 10:00 UTC
**Attendees:** Tejas, Sailesh, Abhilash
**Topic:** Reviewing Phase 1

## Discussion
* **Sailesh** reported that the scaffolding is done. Neo4j and Qdrant are running in Docker. The local connector and GitHub connector are implemented.
* **Abhilash** confirmed Google consent screen is configured.
* **Tejas** was happy with the progress. He highlighted that Step 2 (Connectors) is almost complete.

## Action Items
* **Sailesh**: Implement Gmail and Calendar connector testing (Due: Jul 5).
""",
        "2026-07-06_sprint_2_planning.md": """# Meeting Notes: Sprint 2 Planning
**Date:** 2026-07-06 09:00 UTC
**Attendees:** Tejas, Sailesh, Abhilash
**Topic:** Planning Ingestion Pipeline & Metadata extraction

## Discussion
* **Tejas** kicked off the sprint. The goal is to build the ingestion pipeline.
* **Sailesh** explained the pipeline: chunking raw documents, encoding with `all-MiniLM-L6-v2` into Qdrant, and running chunks through `qwen3:8b` via Ollama to extract metadata nodes like Person, Topic, and Technology, saving them to Neo4j.
* **Abhilash** recommended using a watchdog daemon to monitor the `test-data` folder in real-time.

## Action Items
* **Sailesh**: Implement chunker and embedding logic (Due: Jul 10).
* **Sailesh**: Implement Neo4j node builder (Due: Jul 12).
""",
        "2026-07-08_status_sync.md": """# Meeting Notes: Status Sync
**Date:** 2026-07-08 14:00 UTC
**Attendees:** Sailesh, Tejas, Abhilash
**Topic:** Google OAuth Testing Success

## Discussion
* **Sailesh** shared that the custom Docker WSGI redirect logic successfully ran and fetched emails from Gmail.
* **Abhilash** noted that the calendar query returned a 403 error because the Calendar API was not yet enabled in the Google Developer Console.
* **Sailesh** will enable the Calendar API and re-run.

## Action Items
* **Sailesh**: Enable Calendar API and verify token reuse (Due: Jul 9).
"""
    }

    for name, content in meetings.items():
        with open(os.path.join(MEETINGS_DIR, name), "w", encoding="utf-8") as f:
            f.write(content.strip())
    print(f"Generated {len(meetings)} meeting transcripts in {MEETINGS_DIR}")

def generate_emails():
    """
    Generate 20 mock emails (stored as JSON array objects).
    """
    # Helper to calculate relative times from "now"
    base_time = datetime.now(timezone.utc) - timedelta(days=40)
    
    emails = [
        {
            "id": "msg_001",
            "threadId": "thread_001",
            "subject": "Kickoff: Knowledge Detective Project",
            "from": "Tejas PM <tejas@example.com>",
            "to": "dev-team@example.com",
            "date": (base_time).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi team, I am super excited to launch our new internal RAG tool: Knowledge Detective! The goal is to index and search across local files, emails, calendar invites, and GitHub issues. Let's make sure we meet today for the kickoff meeting.",
            "labelIds": ["INBOX", "UNREAD"]
        },
        {
            "id": "msg_002",
            "threadId": "thread_001",
            "subject": "Re: Kickoff: Knowledge Detective Project",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "Tejas PM <tejas@example.com>, dev-team@example.com",
            "date": (base_time + timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Thanks Tejas! Looking forward to it. I'll make sure the docker stack is ready so we can run Neo4j and Qdrant locally. Privacy is key, so local storage is standard.",
            "labelIds": ["INBOX"]
        },
        {
            "id": "msg_003",
            "threadId": "thread_002",
            "subject": "Architecture choice: Neo4j or PostgreSQL?",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "dev-team@example.com",
            "date": (base_time + timedelta(days=6)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi team, as we prepare for Step 2 of the plan, I want to discuss database storage. Since we have to traverse deep relationships (e.g. email authored by a person who commented on a PR referencing a commit that fixed an issue), should we use Neo4j or PostgreSQL? PostgreSQL is familiar, but Neo4j makes graph traversals very easy.",
            "labelIds": ["SENT"]
        },
        {
            "id": "msg_004",
            "threadId": "thread_002",
            "subject": "Re: Architecture choice: Neo4j or PostgreSQL?",
            "from": "Abhilash SecOps <abhilash@example.com>",
            "to": "Sailesh Architect <sailesh@example.com>, dev-team@example.com",
            "date": (base_time + timedelta(days=6, hours=2)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi Sailesh, I support Neo4j. Since we are running it locally in Docker, keeping the structure as a graph will prevent us from writing hundreds of lines of complex SQL loops. Let's document this as ADR-001.",
            "labelIds": ["INBOX"]
        },
        {
            "id": "msg_005",
            "threadId": "thread_002",
            "subject": "Re: Architecture choice: Neo4j or PostgreSQL?",
            "from": "Tejas PM <tejas@example.com>",
            "to": "Sailesh Architect <sailesh@example.com>, dev-team@example.com",
            "date": (base_time + timedelta(days=7)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Agreed! Plus, in the frontend, I'll be using react-force-graph-2d. It expects nodes and relationships directly in JSON, which fits Neo4j perfectly.",
            "labelIds": ["INBOX"]
        },
        {
            "id": "msg_006",
            "threadId": "thread_003",
            "subject": "Vector DB selection",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "dev-team@example.com",
            "date": (base_time + timedelta(days=11)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi guys, what are your thoughts on storing vector embeddings? We need to save the chunks created by all-MiniLM-L6-v2. Should we use pgvector or Qdrant?",
            "labelIds": ["SENT"]
        },
        {
            "id": "msg_007",
            "threadId": "thread_003",
            "subject": "Re: Vector DB selection",
            "from": "Abhilash SecOps <abhilash@example.com>",
            "to": "Sailesh Architect <sailesh@example.com>, dev-team@example.com",
            "date": (base_time + timedelta(days=11, hours=4)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "I suggest Qdrant. It's written in Rust, super fast, and has a great REST API. Running it in Docker is simple and lightweight. pgvector would require maintaining a Postgres database, which we don't currently need.",
            "labelIds": ["INBOX"]
        },
        {
            "id": "msg_008",
            "threadId": "thread_003",
            "subject": "Re: Vector DB selection",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "Abhilash SecOps <abhilash@example.com>, dev-team@example.com",
            "date": (base_time + timedelta(days=12)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Thanks Abhilash. That makes perfect sense. I will create ADR-002 and add Qdrant to our docker-compose configuration. We will map port 6333.",
            "labelIds": ["SENT"]
        },
        {
            "id": "msg_009",
            "threadId": "thread_004",
            "subject": "Google OAuth Redirect Issues in Docker",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "Abhilash SecOps <abhilash@example.com>",
            "date": (base_time + timedelta(days=18)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hey Abhilash, I am hitting a roadblock testing Google APIs inside Docker. The InstalledAppFlow tries to open a browser inside the container and crashes because it's headless. Any suggestions?",
            "labelIds": ["SENT"]
        },
        {
            "id": "msg_010",
            "threadId": "thread_004",
            "subject": "Re: Google OAuth Redirect Issues in Docker",
            "from": "Abhilash SecOps <abhilash@example.com>",
            "to": "Sailesh Architect <sailesh@example.com>",
            "date": (base_time + timedelta(days=19)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi Sailesh, Google blocks 0.0.0.0 redirects. We should start a temporary WSGI web server on port `8080` inside the container. We can expose that port in Docker, and the user's host browser will redirect to `localhost:8080`, which Docker forwards inside. Let's document this in ADR-003.",
            "labelIds": ["INBOX"]
        },
        {
            "id": "msg_011",
            "threadId": "thread_004",
            "subject": "Re: Google OAuth Redirect Issues in Docker",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "Abhilash SecOps <abhilash@example.com>",
            "date": (base_time + timedelta(days=20)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "That works! I've written a custom server in google_auth.py that intercepts the redirect and overrides the URL mapping. No more invalid_request error. I've also set OAUTHLIB_INSECURE_TRANSPORT = 1 in the environment variables to bypass the HTTPS requirement for localhost.",
            "labelIds": ["SENT"]
        },
        {
            "id": "msg_012",
            "threadId": "thread_005",
            "subject": "Security concern on OAuth tokens",
            "from": "Abhilash SecOps <abhilash@example.com>",
            "to": "Sailesh Architect <sailesh@example.com>",
            "date": (base_time + timedelta(days=21)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi Sailesh, make sure `token.json` and `credentials.json` are added to `.gitignore`. They contain highly sensitive refresh tokens for access to Gmail and Calendar. We cannot push them to the public GitHub repo.",
            "labelIds": ["INBOX"]
        },
        {
            "id": "msg_013",
            "threadId": "thread_005",
            "subject": "Re: Security concern on OAuth tokens",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "Abhilash SecOps <abhilash@example.com>",
            "date": (base_time + timedelta(days=21, hours=1)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Yes, done. Both files are safely added to `.gitignore` and won't be pushed. Thanks for checking!",
            "labelIds": ["SENT"]
        },
        {
            "id": "msg_014",
            "threadId": "thread_006",
            "subject": "Frontend scaffolding: Next.js or React+Vite?",
            "from": "Tejas PM <tejas@example.com>",
            "to": "dev-team@example.com",
            "date": (base_time + timedelta(days=27)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi team, starting Step 8 soon. Should we use Next.js or React + Vite? Vite is faster to bootstrap and keeps everything client-side, which matches our local-first architecture.",
            "labelIds": ["INBOX"]
        },
        {
            "id": "msg_015",
            "threadId": "thread_006",
            "subject": "Re: Frontend scaffolding: Next.js or React+Vite?",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "Tejas PM <tejas@example.com>, dev-team@example.com",
            "date": (base_time + timedelta(days=27, hours=2)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi Tejas, I recommend React + Vite. Since the backend is FastAPI, we don't need SSR (Server Side Rendering). React + Vite is extremely lightweight and loads instantly.",
            "labelIds": ["SENT"]
        },
        {
            "id": "msg_016",
            "threadId": "thread_007",
            "subject": "Timeline and Graph API design",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "Tejas PM <tejas@example.com>, Abhilash SecOps <abhilash@example.com>",
            "date": (base_time + timedelta(days=34)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi Tejas, Abhilash. I am drafting the REST endpoints for Step 7. I will expose `/api/timeline/{topic}` which returns a chronologically sorted list of document chunks containing references to the topic. I will also expose `/api/graph/{entity}` for the knowledge graph.",
            "labelIds": ["SENT"]
        },
        {
            "id": "msg_017",
            "threadId": "thread_007",
            "subject": "Re: Timeline and Graph API design",
            "from": "Tejas PM <tejas@example.com>",
            "to": "Sailesh Architect <sailesh@example.com>, Abhilash SecOps <abhilash@example.com>",
            "date": (base_time + timedelta(days=34, hours=3)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Awesome Sailesh. For `/api/graph/{entity}`, can you make sure it returns both nodes and edges? Each node should have a type (Person, Document, Email, Issue, Commit) so I can color-code them.",
            "labelIds": ["INBOX"]
        },
        {
            "id": "msg_018",
            "threadId": "thread_007",
            "subject": "Re: Timeline and Graph API design",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "Tejas PM <tejas@example.com>, Abhilash SecOps <abhilash@example.com>",
            "date": (base_time + timedelta(days=35)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Yes, the JSON structure will be exactly: `{ 'nodes': [ { 'id': '...', 'label': '...', 'type': '...' } ], 'edges': [ { 'source': '...', 'target': '...', 'type': '...' } ] }`. This is standard for react-force-graph.",
            "labelIds": ["SENT"]
        },
        {
            "id": "msg_019",
            "threadId": "thread_008",
            "subject": "Calendar Sync issues",
            "from": "Tejas PM <tejas@example.com>",
            "to": "Sailesh Architect <sailesh@example.com>",
            "date": (base_time + timedelta(days=37)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Hi Sailesh, I noticed in our logs that Calendar connector returns a 403 error. Did you verify if the Google Calendar API is enabled in your GCP project settings? Let me know.",
            "labelIds": ["INBOX"]
        },
        {
            "id": "msg_020",
            "threadId": "thread_008",
            "subject": "Re: Calendar Sync issues",
            "from": "Sailesh Architect <sailesh@example.com>",
            "to": "Tejas PM <tejas@example.com>",
            "date": (base_time + timedelta(days=37, hours=1)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "body": "Ah, nice catch! It was enabled in the GCP console but it took a few minutes to propagate. It is working now and returns all meetings. Thanks!",
            "labelIds": ["SENT"]
        }
    ]

    for email in emails:
        file_path = os.path.join(EMAILS_DIR, f"{email['id']}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(email, f, indent=2)
    print(f"Generated {len(emails)} email JSON files in {EMAILS_DIR}")

def generate_readme():
    """
    Generate README.md for test data.
    """
    readme = """# Knowledge Detective Synthetic Test Corpus

This folder contains the mock data representing a software engineering team building the **Knowledge Detective** project.

## Directory Structure
* `docs/`: Product specs and Architecture Decision Records (ADRs) in markdown format.
* `meetings/`: Markdown meeting logs and transcripts.
* `emails/`: Individual email threads saved in JSON format.

## Team Profile
* **Tejas** (`tejas@example.com`): Product & Frontend
* **Sailesh** (`sailesh@example.com`): Lead Architect / Backend Engineer
* **Abhilash** (`abhilash@example.com`): SecOps / Infra Engineer

## Cross-Source Traversal Narrative
The files contain a connected thread of decisions regarding databases and libraries:
1. **Goal Setting**: Initiated in Kickoff Meeting (`meetings/2026-06-01_kickoff_meeting.md`) and email `msg_001`.
2. **Graph DB decision (Neo4j)**: Initiated in email `msg_003`, reviewed in `meetings/2026-06-08_architecture_review.md`, and formalized in `docs/ADR-001-graph-database.md`.
3. **Vector DB decision (Qdrant)**: Discussed in email `msg_006`, decided in `meetings/2026-06-13_database_decision_sync.md`, and formalized in `docs/ADR-002-vector-database.md`.
4. **Google OAuth & Redirects**: Designed in `meetings/2026-06-20_oauth_planning.md`, email `msg_009`, and formal specification in `docs/ADR-003-google-oauth.md`.
5. **Frontend stack (React + Vite)**: Discussed in email `msg_014`, meeting `meetings/2026-06-29_frontend_sync.md`, and formalized in `docs/frontend_architecture.md`.
"""
    with open(os.path.join(TEST_DATA_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme.strip())
    print(f"Generated README.md in {TEST_DATA_DIR}")

if __name__ == "__main__":
    ensure_dirs()
    generate_docs()
    generate_meetings()
    generate_emails()
    generate_readme()
    print("Synthetic test data generation complete!")
