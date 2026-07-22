# Real-Time Chat Platform — Project Context

## Overview
Production-ready FastAPI application for real-time multi-user chat. Public, private (1:1),
and group conversations, instant delivery over WebSockets, notifications over SSE, all data
in PostgreSQL.

**Team:** Ahmed & Ismail — 5-day sprint, 2 people × 4 hrs/day
**Frontend:** React + Tailwind, starts after backend core is stable (not in this repo's scope yet)

## Tech Stack
- FastAPI
- SQLAlchemy 2.0 (async) + asyncpg
- PostgreSQL / Supabase
- Alembic (migrations)
- WebSockets (native FastAPI/Starlette)
- SSE via `sse-starlette`
- JWT auth (access + refresh tokens)
- Password hashing: argon2
- Structured logging: `structlog`

## Architecture: Hexagonal / Clean Architecture

Strict layering — dependencies point inward. Outer layers depend on inner layers, never
the reverse.

```
app/
├── domain/
│   ├── entities/          # Pure Python domain objects. No ORM, no Pydantic, no FastAPI.
│   ├── repositories/      # Abstract interfaces (ports) — e.g. UserRepository ABC.
│   └── services/          # Pure domain logic spanning entities (e.g. role/permission rules).
│
├── application/
│   ├── use_cases/         # One class/function per action. Orchestrates domain + repo ports.
│   └── dto/                # Pydantic request/response schemas (API contracts).
│
├── infrastructure/
│   ├── database/           # Async engine, session factory, SQLAlchemy Base, ORM models.
│   ├── repositories/       # Concrete implementations of domain/repositories interfaces.
│   ├── websocket/          # ConnectionManager, broadcast logic, SSE publishers.
│   └── logging/            # structlog setup/handlers.
│
├── api/
│   ├── routes/              # FastAPI routers (REST endpoints).
│   ├── websocket/           # WS route handlers, wired to infrastructure/websocket.
│   └── dependencies/        # Depends() providers — composition root wiring infra into use cases.
│
├── core/
│   ├── config.py            # Env-based settings (pydantic-settings).
│   ├── security.py          # Password hashing, JWT create/verify.
│   └── logger.py             # structlog configuration.
│
├── tests/
└── main.py
```

### Layering rules
- `domain/` has zero external dependencies (no SQLAlchemy, no Pydantic, no FastAPI imports).
- `application/use_cases/` depend only on `domain/` interfaces — never import concrete
  infrastructure classes directly (always via dependency injection through `api/dependencies`).
- `application/dto/` defines API-facing request/response shapes — distinct from domain
  entities and ORM models. Never leak ORM models or password hashes into a DTO response.
- `infrastructure/` implements the ports defined in `domain/repositories/`.
- `api/dependencies/` is the composition root: this is where concrete infra
  (SQLAlchemy repos, JWT provider, connection manager) gets instantiated and injected
  into use cases via `Depends()`.
- Real-time broadcast (WebSocket) and notifications (SSE) both go through a shared
  publisher port so use cases (e.g. `SendMessage`) don't know or care which transport
  delivers the event.

## Data flow example (registration)
```
HTTP request
  → RegisterUserRequest (DTO, application/dto) — validates input
  → RegisterUser use case (application/use_cases) — works with User domain entity
  → UserRepository port → SQLAlchemy repo (infrastructure) — persists ORM model
  → use case returns domain entity
  → route maps entity → UserResponse (DTO) → HTTP response
```

## Task Plan (5-Day Sprint)

### Day 1 — Project Setup, Database & Core Security
Goal: repo running locally, schema migrated, auth utilities ready for Day 2.

| # | Task | Layer(s) | Owner |
|---|------|----------|-------|
| 1 | Apply finalized `schema.sql` to Postgres/Supabase, init Alembic, generate baseline migration, seed script (test users + singleton public conversation) | `infrastructure/database` | Ahmed |
| 2 | SQLAlchemy 2.0 async ORM models for every table (relationships, constraints) + Pydantic DTOs for User and Auth | `infrastructure/database` + `application/dto` | Ismail |
| 3 | Scaffold clean-architecture folders, `core/config.py`, docker-compose for local Postgres, base `main.py` with health-check route, `core/logger.py` (structlog) + request/response logging middleware | `core` (cross-cutting) | Ahmed |
| 4 | `core/security.py`: password hashing (argon2), JWT access/refresh token creation and verification, `get_current_user` dependency stub | `core` + `api/dependencies` | Ismail |

### Day 2 — Authentication & User Management
Goal: full auth flow working end-to-end (register, login, refresh, protected routes) plus profile/search endpoints.

| # | Task | Layer(s) | Owner |
|---|------|----------|-------|
| 1 | Registration and login endpoints, incl. validation and duplicate email/username handling | `application/use_cases` + `api/routes` | Ahmed |
| 2 | Refresh token endpoint (rotation + revocation), logout endpoint, wire `get_current_user` as a real dependency guarding protected routes | `application/use_cases` + `api/dependencies` | Ismail |
| 3 | Profile endpoints: get own profile, update profile (display name, avatar, bio), online/offline status toggle | `application/use_cases` + `api/routes` | Ahmed |
| 4 | User search endpoint (trigram search on username), `last_seen_at` update logic triggered on activity | `application/use_cases` + `infrastructure/repositories` | Ismail |

### Day 3 — Conversations: Public, Private & Group Chat
Goal: all three conversation types can be created, joined, and listed via REST.

| # | Task | Layer(s) | Owner |
|---|------|----------|-------|
| 1 | Ensure singleton public conversation exists on startup; endpoint to fetch/join the global room | `application/use_cases` + `api/routes` | Ahmed |
| 2 | Start/get-or-create 1:1 private conversation between two users, conversation history endpoint with pagination | `application/use_cases` + `infrastructure/repositories` | Ismail |
| 3 | Create group and join group endpoints (role assignment on creation, membership checks) | `application/use_cases` + `api/routes` | Ahmed |
| 4 | Leave group endpoint, membership/role management (promote, demote, remove member as admin/owner) | `domain/services` (role rules) + `application/use_cases` | Ismail |

### Day 4 — Messaging Core & Real-Time WebSockets
Goal: messages can be sent/edited/deleted/searched via REST, delivered instantly via WebSocket.

| # | Task | Layer(s) | Owner |
|---|------|----------|-------|
| 1 | Send message endpoint (REST fallback/history write path), edit message endpoint (`is_edited`/`edited_at` handling) | `application/use_cases` + `api/routes` | Ahmed |
| 2 | Delete message endpoint (soft delete), message search endpoint using tsvector/GIN index | `application/use_cases` + `infrastructure/repositories` | Ismail |
| 3 | In-memory WebSocket connection manager: authenticated connect/disconnect handshake, per-conversation subscriber tracking, structured logging of connect/disconnect/auth-failure events | `infrastructure/websocket` + `infrastructure/logging` | Ahmed |
| 4 | Real-time message broadcast over WebSocket on send, typing indicator events (start/stop), structured logging of broadcast fan-out and delivery failures | `infrastructure/websocket` + `infrastructure/logging` | Ismail |

### Day 5 — Read Status, SSE Notifications & Integration
Goal: unread/read tracking complete, SSE notifications live, reconnection handled, core flows tested.

| # | Task | Layer(s) | Owner |
|---|------|----------|-------|
| 1 | Fan-out `message_read_status` rows on send (one per recipient), mark-as-read endpoint, per-conversation unread count endpoint | `application/use_cases` + `infrastructure/repositories` | Ahmed |
| 2 | SSE endpoint streaming new-message notifications and system announcements (`sse-starlette`) | `infrastructure/websocket` (SSE) + `api/routes` | Ismail |
| 3 | WebSocket reconnection handling (client retry contract), connection cleanup on disconnect (status → offline, `last_seen_at` update) | `infrastructure/websocket` | Ahmed |
| 4 | End-to-end tests for auth, WebSocket messaging, SSE flows; verify structured logs across all three; final pass on OpenAPI docs | `tests/` (cross-cutting) | Ismail |

### Out of scope for this sprint (optional / deferred)
- Friend requests
- System announcement authoring UI
- Background task progress tracking
- React + Tailwind frontend (begins once backend core is stable)

## Logging Convention
`core/logger.py` (structlog) is set up on Day 1 and used throughout:
- Request/response logging middleware in the `api` layer
- Use-case-level logs in `application`
- WebSocket/SSE event logs in `infrastructure`

Each person logs from their own layer as they build it, rather than retrofitting later.

## Working Agreements
- `domain/repositories` interfaces and `infrastructure/database` Base/ORM models are
  shared touchpoints — agree on file ownership before both people edit them to avoid
  merge conflicts.
- DTOs (`application/dto`) describe API contracts, not DB columns — never expose
  internal fields (e.g. password hashes) in a response DTO.
- New tables/columns require a matching Alembic migration, not manual schema edits.
