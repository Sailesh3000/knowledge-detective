# Meeting Notes: Kickoff Meeting
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