# Knowledge Detective Synthetic Test Corpus

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