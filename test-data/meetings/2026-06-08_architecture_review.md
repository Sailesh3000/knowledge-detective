# Meeting Notes: Architecture Review
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