# Architecture Decision Record (ADR) 001: Graph Database Selection

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