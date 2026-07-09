# Product Requirements Document (PRD): Knowledge Detective

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