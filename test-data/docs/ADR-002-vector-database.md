# Architecture Decision Record (ADR) 002: Vector Database Selection

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