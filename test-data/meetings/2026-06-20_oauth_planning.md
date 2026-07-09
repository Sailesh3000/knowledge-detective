# Meeting Notes: OAuth and Security Planning
**Date:** 2026-06-20 09:30 UTC
**Attendees:** Abhilash, Sailesh
**Topic:** Google API Authentication in Docker

## Discussion
* **Abhilash** pointed out that running inside a headless Docker container makes standard Google auth flow crash since it tries to open a browser window on the container OS.
* **Sailesh** suggested using a static verification code copy-paste method.
* **Abhilash** noted that Google has officially deprecated Out-Of-Band (OOB) auth flow, so copy-paste codes are no longer supported.
* **Sailesh** proposed starting a temporary WSGI web server on port `8080` inside the container. We can expose that port in Docker, and the user's host browser will redirect to `localhost:8080`, which Docker forwards inside.

## Action Items
* **Abhilash**: Write ADR-003 and configure the GCP consent screen for testing (Due: Jun 22).
* **Sailesh**: Write the custom WSGI server inside `google_auth.py` (Due: Jun 25).