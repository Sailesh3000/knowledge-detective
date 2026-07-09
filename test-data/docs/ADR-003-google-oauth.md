# Architecture Decision Record (ADR) 003: Google OAuth for Headless/Docker Development

**Author:** Abhilash (Security & Infra)
**Date:** 2026-06-21
**Status:** Accepted

## Context
Our backend runs inside a headless Docker container. Google's standard OAuth helper (`InstalledAppFlow`) assumes a browser is available locally on the machine running the code to complete the OAuth consent page redirect.

## Decision
We will override `google_auth_oauthlib`'s flow by writing a custom WSGI server inside the container that:
1. Registers `http://localhost:8080/` as the callback redirect (allowed by Google).
2. Binds the server socket to `0.0.0.0:8080` (enabling Docker's port mapping to forward the host browser's redirect request into the container).
3. Replaces `0.0.0.0` or raw container IPs in the callback response URI with `localhost` to satisfy local transport checks.
4. Uses `OAUTHLIB_INSECURE_TRANSPORT = 1` for local HTTP verification.

## Consequences
* Users must run Docker mapping `-p 8080:8080`.
* The `token.json` containing credentials will be cached in the mounted directory.