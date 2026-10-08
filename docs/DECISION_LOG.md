# SWASTHYA — DECISION LOG

> Record of finalized project decisions.
> This document preserves the reasoning and implementation implications of important architectural and project decisions.

---

## Decision 001 — Canonical Environment Configuration

**Date:** 2026-10-08

**Section:** Environment Configuration

**Status:** DECIDED

### Decision

Swasthya will use a **single root `.env` file as the canonical local environment configuration** for the entire repository.

The repository will contain:

```text
Swasthya/
├── .env.example
├── .env
├── docker-compose.yml
├── backend/
├── frontend/
└── docs/

The actual .env file is local-only and must never be committed.

.env.example is the committed, public-safe configuration template.

There will be no separate backend/.env or backend/.env.example as an independent configuration source.

Reason / Rationale

The project is a single repository containing the backend, frontend, agent layer, infrastructure, and supporting services.

Maintaining multiple environment files creates ambiguity about which configuration is authoritative and can cause Docker Compose and Django to read different values.

A single root environment configuration gives the project one clear source for local configuration and reduces configuration drift.

Implementation Implications
Move the canonical environment template to the repository root.
Django configuration will use the root environment configuration.
Docker Compose will use the root environment configuration.
The backend must not maintain a competing environment template.
Claude 1's existing backend/.env.example must be removed or replaced as part of the approved correction.
Docker Compose configuration must be corrected so that environment-variable interpolation behaves consistently.
Environment configuration must remain compatible with both local development and Docker-based development.
The exact production environment mechanism may be decided separately later.
Constraints / Non-Negotiable Rules
Never commit .env.
Never put real API keys, passwords, tokens, or secrets in .env.example.
.env.example must contain placeholders only.
Do not create duplicate environment configuration sources.
Do not silently introduce new environment variables without documenting them.
Environment configuration must not change the ownership boundaries between Claude workstreams.
Supersedes

Claude 1's initial Phase 1 implementation, which contains:

/backend/.env.example

and a separate backend environment arrangement.

That implementation is frozen and will be corrected before integration.

Related Sections
Project Security
Git Repository
Docker / Infrastructure
Backend Configuration
Claude 1 Workstream
Claude 2 Workstream
Claude 4 Workstream