# Meeting Notes: Database Decision Sync
**Date:** 2026-06-13 11:00 UTC
**Attendees:** Sailesh, Abhilash
**Topic:** Vector Database - pgvector vs Qdrant

## Discussion
* **Sailesh** suggested pgvector since we are already using Postgres for other tasks.
* **Abhilash** countered: We don't have Postgres in the plan! Keeping it simple with Qdrant is better because Qdrant is lightweight, has a built-in search UI dashboard, and is optimized for CPU similarity search.
* **Sailesh** reviewed Qdrant's specs and agreed. Running Qdrant in Docker takes less than 50MB of RAM.

## Action Items
* **Sailesh**: Write ADR-002 recommending Qdrant and update `docker-compose.yml` (Due: Jun 15).