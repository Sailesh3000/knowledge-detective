# Knowledge Detective — 4-Day Build Plan
### Using $100 AMD Developer Cloud GPU Credits + $50 Fireworks AI API Credits

---

## 1. Resource-to-Architecture Mapping

Your two credit pools map naturally onto two different jobs in the pipeline. Don't blur them — this keeps costs predictable and avoids burning GPU credits on things an API call does cheaper.

| Resource | What it's good for | What you'll use it for |
|---|---|---|
| **Fireworks AI ($50 API credits)** | Fast, cheap, pay-per-token inference on hosted open models (function-calling, JSON mode, embeddings) | The **reasoning agent** (Gemma) that plans queries, traverses the graph, verifies evidence, and writes the final answer |
| **AMD Developer Cloud ($100 GPU credits)** | Renting raw GPU instances (MI300X / MI250 class) by the hour | Hosting **Neo4j + Qdrant** on a single beefy VM, running **local embedding generation** in bulk, and optionally self-hosting a second model if Fireworks costs run hot |

**Why split it this way:** Fireworks bills per-token, which is perfect for an agent that's calling the model dozens of times per query (planning → retrieval → verification → answer). AMD GPU credits bill per-hour whether you use the GPU or not, so they're best spent on a persistent service (your databases) or a batch job (embedding your whole corpus once), not on interactive chat inference.

---

## 2. Budget Plan (so you don't run out mid-hackathon)

### Fireworks AI — $50 budget
Gemma models on Fireworks are priced per million tokens (check current rates in-app before committing — Fireworks pricing pages change). Assume roughly:
- Planning/decomposition calls: ~500 tokens in/out × maybe 300 queries during dev+demo = cheap, well under $5
- Evidence verification + answer synthesis: larger context (2-8k tokens per call) × 300 queries ≈ $10-20
- Embedding calls (if you use Fireworks' embedding endpoint instead of local): a few dollars for a small corpus

**Reserve at least $15-20 of the $50 for the live demo and judge Q&A** — don't burn it all in development. Set a budget alert in the Fireworks dashboard on day 1.

### AMD Developer Cloud — $100 budget
- Spin up **one mid-tier GPU instance** (don't grab the biggest MI300X node — you don't need it for Neo4j/Qdrant, which are CPU/RAM-bound, not GPU-bound, for a dataset this small)
- Actually — important insight: **Neo4j and Qdrant don't need a GPU at all** for a corpus of a few hundred to a few thousand documents. The GPU credits are best spent on:
  1. A **CPU-heavy instance** if AMD Developer Cloud offers non-GPU tiers under the same credit pool (check their console — sometimes CPU instances are billed from the same credit balance at a much lower rate), OR
  2. A GPU instance used specifically for **local embedding model inference** (e.g., running `BAAI/bge-large` or `nomic-embed-text` locally via `sentence-transformers` with ROCm) so you don't pay Fireworks per-embedding-token, OR
  3. **Self-hosting Gemma via vLLM/ROCm** as a fallback if Fireworks rate limits you during the live demo

**Recommended allocation:**
- Day 1: spin up one GPU instance (~$0.50-2/hr depending on tier), leave it running through Day 4 for the databases + embedding service. At ~$1.50/hr × 96 hours ≈ $144 — **too much**. So instead: stop/pause the instance overnight (AMD Developer Cloud typically bills only while running). Realistic usage: ~10-12 active hours/day × 4 days × ~$1.50/hr ≈ $60-70, leaving buffer.
- Keep $20-30 GPU credit in reserve for the final demo day so the instance definitely doesn't get killed mid-presentation.

---

## 3. System Architecture (as it will actually run)

```
                        ┌─────────────────────────────┐
                        │   AMD Developer Cloud GPU VM │
                        │  (single instance, ROCm)     │
                        │                              │
                        │  ┌────────┐   ┌────────────┐ │
                        │  │ Neo4j  │   │  Qdrant     │ │
                        │  │ (graph)│   │ (vectors)   │ │
                        │  └────────┘   └────────────┘ │
                        │  ┌────────────────────────┐  │
                        │  │ Local embedding model   │  │
                        │  │ (sentence-transformers, │  │
                        │  │  ROCm-accelerated)       │  │
                        │  └────────────────────────┘  │
                        └───────────────┬──────────────┘
                                        │  REST/Bolt
                                        │
        ┌───────────────────────────────┴───────────────────────────┐
        │                     Backend (FastAPI)                     │
        │  - Ingestion connectors (Gmail, GitHub, GMeet/Cal, Local) │
        │  - Metadata extraction (entities, dates, authors, links)  │
        │  - Query planner → calls Fireworks AI                     │
        │  - Evidence retrieval orchestration (graph + vector)      │
        │  - Evidence verification → calls Fireworks AI             │
        └───────────────┬─────────────────────────────┬─────────────┘
                         │                             │
                ┌────────┴────────┐          ┌─────────┴─────────┐
                │ Fireworks AI API │          │  Frontend (React) │
                │  Gemma model:     │          │  - Chat UI         │
                │  - plan queries   │          │  - Timeline view   │
                │  - verify evidence│          │  - Graph viz       │
                │  - write answer   │          │    (e.g. react-force-graph)│
                └───────────────────┘          └────────────────────┘
```

---

## 4. Day-by-Day Plan

### **Day 1 — Infrastructure + Ingestion**
**Goal: data flowing into the graph and vector store by end of day.**

1. **Set up accounts & budgets**
   - Create AMD Developer Cloud account, redeem the $100 credit, spin up one GPU instance (start small — you can resize later). Install ROCm drivers if not preinstalled, Docker, Docker Compose.
   - Create Fireworks AI account, redeem $50 credit, generate an API key, set a spend alert.
2. **Deploy databases on the AMD instance** (docker-compose):
   - Neo4j (community edition is fine) — exposed on bolt port
   - Qdrant — exposed on REST port
   - *(Tip: bind both to the VM's private network only, and tunnel via SSH or a simple auth-protected reverse proxy for your dev laptop — don't expose Neo4j/Qdrant unauthenticated to the public internet.)*
3. **Build connectors** (Python, FastAPI backend):
   - **Gmail connector**: use Gmail API to pull emails from specific threads or labels. Extract: sender, receiver, timestamp, subject, and text body.
   - **GitHub connector**: use GitHub REST/GraphQL API (`PyGithub` or raw `requests`) to pull issues, PRs, commits, and comments. Extract: author, timestamp, linked issue/PR numbers, text body.
   - **Google Meet/Calendar connector**: use Calendar API for meeting metadata (attendees, times, descriptions) and integrate Meet transcripts if available.
   - **Local folders connector**: local folder ingestion using `pypdf`/`markdown-it-py` to extract text + basic metadata (filename, modified date) from PDFs, Markdown, and TXT files.
4. **Metadata extraction pass**: for each ingested item, extract entities/dates/authors either with simple regex+heuristics (fast, free) or one lightweight Fireworks/Gemma call per batch (cheap if batched — send 10-20 documents per call, ask for structured JSON metadata back).
5. **End of day checkpoint**: raw documents ingested, chunked, and stored with metadata in Postgres/SQLite (simple relational store for raw text) — graph and vectors come Day 2.

### **Day 2 — Knowledge Graph + Vector Store**
**Goal: every document embedded, and explicit relationships materialized in Neo4j.**

1. **Embeddings**: run your local embedding model on the AMD GPU instance (e.g., `sentence-transformers/all-mpnet-base-v2` or `BAAI/bge-base-en-v1.5` via ROCm-accelerated PyTorch) over every chunk. Push vectors + metadata into Qdrant. This is the single most GPU-hungry step — do it once, in batch, not per-query.
2. **Graph construction (Data Unification Strategy)**:
   - **Nodes**: `Email`, `PR`, `Commit`, `Issue`, `Meeting`, `LocalDoc`, `Person`, `Topic`, `Decision`
   - **Edges**: `MENTIONS`, `AUTHORED_BY`, `ATTENDED`, `RESOLVES`, `REFERENCES`, `PRECEDES` (temporal), `SAME_AS` (identity)
   - **How to combine disparate sources**:
     1. **Identity Resolution (The Glue)**: A developer might be `user@gmail.com` in email/calendar, `user99` on GitHub, and "User Name" in a local document. You will extract these aliases and map them to a unified `Person` node (or link alias nodes with `SAME_AS` edges). This instantly connects a GitHub PR to a Google Meet they attended.
     2. **Explicit References**: Extract URLs and ID patterns using regex during ingestion. If an email body contains `github.com/repo/pull/123`, create a hard `REFERENCES` edge between the `Email` node and the `PR` node.
     3. **Temporal Alignment**: Every source has a timestamp (email sent, PR opened, meeting occurred, file modified). Use these to create chronological `PRECEDES` chains for timeline reconstruction, even across different sources.
     4. **Semantic Extraction (Topics)**: During the LLM metadata extraction step, ask Gemma to identify key `Topic` or `Project` names from the text. Link the source document to these `Topic` nodes, allowing you to easily query "Show me all Emails, PRs, and Meetings related to the 'Auth Migration' topic."
     5. **LLM-Inferred Links**: Only use the LLM to infer soft links (e.g., "this email and this PR are about the same decision") when explicit links are absent. Mark these edges as `inferred: true` with a confidence score so the UI can visually distinguish hard evidence vs. AI guesses.
3. **Sanity-check the graph**: run a few Cypher queries manually in Neo4j Browser to confirm the shape looks right before building the agent on top of it.

### **Day 3 — Reasoning Agent (Fireworks AI) + Core Q&A Flow**
**Goal: "Ask a question" feature working end-to-end with citations.**

1. **Wire up Fireworks AI** in the backend:
   ```python
   import requests

   FIREWORKS_API_KEY = "..."
   response = requests.post(
       "https://api.fireworks.ai/inference/v1/chat/completions",
       headers={"Authorization": f"Bearer {FIREWORKS_API_KEY}"},
       json={
           "model": "accounts/fireworks/models/gemma-<version>",
           "messages": [{"role": "user", "content": prompt}],
           "response_format": {"type": "json_object"},
           "max_tokens": 1000,
       },
   )
   ```
   *(Confirm the exact current Gemma model slug and JSON-mode support in the Fireworks docs/console before hardcoding — model names/versions change.)*

2. **Implement the pipeline** exactly as your design doc lays out:
   - **Planner call**: given the user question, ask Gemma to decompose it into sub-queries and decide which sources (graph traversal vs. vector search vs. both) are needed. Force structured JSON output (`{"sub_queries": [...], "search_type": "graph|vector|hybrid"}`).
   - **Retrieval**: execute the plan — vector search in Qdrant for semantic matches, Cypher traversal in Neo4j for explicit relationship chains.
   - **Verification call**: feed retrieved evidence back to Gemma, ask it to only use claims it can trace to a specific document ID, and to explicitly flag gaps ("no final decision found") rather than fill them in.
   - **Answer synthesis**: final Gemma call produces the user-facing answer with inline citations (`[Doc: PR#231]`, `[Doc: Slack 2024-06-02]`).
3. **Guardrail prompt pattern** (put this in your system prompt for the verification/synthesis steps):
   > "Only state facts present in the provided evidence. For every claim, cite the source ID. If evidence is insufficient or contradictory, say so explicitly instead of guessing."
4. **Build a minimal frontend** (React) with a chat box that shows the answer + a "sources" panel listing cited documents with links back to GitHub/file.

### **Day 4 — Timeline, Graph Viz, Polish, Demo Prep**
**Goal: the other two "polished capabilities" + a rehearsed demo.**

1. **Decision Timeline view**: query Neo4j for the `PRECEDES` chain around a topic, render as a simple vertical timeline component (dates on the left, evidence cards on the right, each linking to the source).
2. **Knowledge Graph Visualization**: use `react-force-graph` or `vis-network` to render the local neighborhood around a queried entity (e.g., "OAuth" → connected PRs, docs, people). Keep it scoped to 1-2 hop neighborhoods — a full-graph render will be unreadable and slow.
3. **Missing-information + duplicate-detection features**: these are largely "free" once the pipeline above works — they're just specific prompt templates over the same retrieval pipeline (ask Gemma to compare a new question against retrieved evidence and report confidence/gaps).
4. **Cost check-in**: verify both credit balances aren't near zero. Cache/pre-run your 3-4 demo queries once so you have both a "live" and a "known-good cached" path in case of API hiccups during the presentation.
5. **Demo script** (rehearse this, 3-4 minutes):
   - Ask a real "why did we do X" question live → show planner → evidence → cited answer
   - Show the Decision Timeline for that same topic
   - Show the Knowledge Graph viz zoomed to that entity
   - Ask one question with **no answer in the corpus** to demonstrate the "we don't fabricate" behavior explicitly — this is your strongest differentiator, make sure judges see it

---

## 5. Key Engineering Decisions & Why

- **Explicit links before inferred links.** GitHub already gives you PR↔commit↔issue relationships for free — use the API's native linkage rather than asking an LLM to guess it. Save LLM inference for genuinely ambiguous cross-source connections (e.g., Slack message ↔ PR), and mark those edges as inferred with a confidence score.
- **Batch embeddings locally on the AMD GPU, not per-query via API.** This is the difference between a one-time GPU cost and an ongoing per-token cost — embed once at ingestion time, not on every user question.
- **Keep the databases unauthenticated-but-private.** Bind Neo4j/Qdrant to localhost or a private network on the AMD instance; don't spend hackathon time hardening auth you don't need for a demo, but also don't expose them publicly by accident.
- **Structured JSON outputs at every LLM step.** Function-calling/JSON mode on Fireworks makes the planner → retrieval → verification pipeline much easier to wire together reliably than parsing free-text.
- **Scope connectors to 4 sources** (Gmail, GitHub, Google Meet/Calendar, Local folders). Be prepared to handle OAuth flows for Google APIs (Gmail, Calendar). To save time during the hackathon, consider using personal service accounts or desktop OAuth flows with pre-consented test users.

---

## 6. Risk List (things that commonly blow up hackathon budgets/timelines)

| Risk | Mitigation |
|---|---|
| GPU instance left running overnight burns credits fast | Stop/pause the instance each night; only Day 4 should run continuously through the demo |
| Fireworks rate limits or model unavailable mid-demo | Pre-cache 3-4 demo query results as a fallback; know the current Gemma model slug ahead of time (verify in Fireworks console, don't assume from memory) |
| Graph gets noisy from over-eager LLM-inferred edges | Only infer edges when no explicit link exists, and tag confidence so bad edges are visually distinguishable, not silently trusted |
| Embedding job takes longer than expected on Day 2 | Start with a small subset (50-100 docs) to validate the pipeline before running the full corpus |
| Frontend graph viz becomes unreadable with full dataset | Always query a scoped 1-2 hop neighborhood, never render the entire graph |

---

## 7. What to Verify Before You Start (things that change over time)

Before committing code, check current details in each platform's dashboard/docs rather than assuming:
- Exact Gemma model version/slug currently hosted on Fireworks AI, and whether it supports JSON mode / function calling
- Current Fireworks pricing per million tokens for that model
- AMD Developer Cloud's available instance tiers, whether non-GPU/CPU-only instances exist under the same credit pool, and the exact hourly rates
- Whether AMD Developer Cloud bills while an instance is stopped (usually not, but confirm) — this determines your night-time cost strategy

This keeps your 4-day build realistic against a $150 combined budget while still hitting all three MVP capabilities from your design doc: **ask a question with cited evidence, show a decision timeline, and visualize the knowledge graph.**
