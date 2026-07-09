# Backend API Endpoint Specifications

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