# Meeting Notes: Sprint 2 Planning
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