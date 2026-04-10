# DAItaView — Architecture

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Service Topology](#2-service-topology)
3. [Frontend](#3-frontend)
4. [API Service](#4-api-service)
5. [Query Pipeline](#5-query-pipeline)
6. [Knowledge System](#6-knowledge-system)
7. [Code Execution Engine](#7-code-execution-engine)
8. [Data Model](#8-data-model)
9. [Authentication & Authorization](#9-authentication--authorization)
10. [Audit Logging](#10-audit-logging)
11. [Data Flow: End-to-End Query](#11-data-flow-end-to-end-query)
12. [Security Model](#12-security-model)
13. [Configuration Reference](#13-configuration-reference)

---

## 1. System Overview

DAItaView is a company-level AI data reporting platform. Business users ask natural language questions about company data and receive interactive visualizations. The central differentiator is an admin-curated **knowledge curriculum**: data admins teach the system company-specific context (business rules, table semantics, example queries) via a Markdown editor. The LLM reads this curriculum before generating code, and surfaces structured clarification questions when knowledge is insufficient.

**Key properties:**
- Multi-user, role-based access control (RBAC)
- Source-level and table-level data permission enforcement
- LLM reasoning phase before code generation — asks before guessing
- Sandboxed code execution in a dedicated Docker container
- Full audit log of all query, admin, and auth events
- Persistent chat sessions with multi-turn context
- Staleness tracking: results display when data was last fetched, with one-click refresh

---

## 2. Service Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Network: daitaview                │
│                                                                  │
│  ┌──────────────┐   HTTP / WS    ┌─────────────────────────┐   │
│  │   Frontend   │ ◄────────────► │       API Service        │   │
│  │  React/Vite  │                │       FastAPI/Python      │   │
│  │  port 3000   │                │       port 8000           │   │
│  └──────────────┘                └──────┬──────────┬─────────┘   │
│                                         │          │             │
│                              SQL (async)│          │HTTP         │
│                                         ▼          ▼             │
│                              ┌──────────────┐  ┌──────────────┐ │
│                              │  PostgreSQL  │  │  Execution   │ │
│                              │  (pgvector)  │  │   Service    │ │
│                              │  port 5432   │  │  (internal)  │ │
│                              └──────────────┘  └──────────────┘ │
│                                                                  │
│  External: Anthropic Claude API  (outbound from API service)     │
└─────────────────────────────────────────────────────────────────┘
```

| Service | Image | Ports | Network Access |
|---|---|---|---|
| `frontend` | Node/Vite build | 3000 (public) | Talks to `api` |
| `api` | Python 3.11 | 8000 (public) | Talks to `db`, `execution`, Anthropic API |
| `execution` | Python 3.11 slim | internal only | No external network; only reachable from `api` |
| `db` | `pgvector/pgvector:pg16` | 5432 (public for dev) | Internal |

**Execution isolation:** The execution container uses `expose` (not `ports`), drops all Linux capabilities (`cap_drop: ALL`), and sets `no-new-privileges`. It cannot initiate outbound connections.

---

## 3. Frontend

**Stack:** React 18, TypeScript, Vite, React Router v6, TanStack Query v5, Axios, Plotly.js, Monaco Editor.

### Directory Structure

```
frontend/src/
├── api/
│   └── client.ts           # Axios instance with JWT injection & 401 redirect
├── components/
│   ├── NavBar              # Top bar: user display, logout, admin link (role-gated)
│   ├── ProtectedRoute      # Redirects to /login if unauthenticated
│   ├── SessionSidebar      # Grouped session list (Pinned / Today / Yesterday / Older)
│   ├── NewChatModal        # Source picker → creates session → navigates to /chat/:id
│   ├── TurnMessage         # Renders one Q&A turn (thinking block, result, code block)
│   ├── ClarificationCard   # Displays saved clarification Q&A from turn history
│   ├── StalenessBar        # "Last updated" badge + per-turn Refresh button
│   ├── ChartResult         # Plotly renderer with CSV export
│   ├── TableResult         # Sortable paginated table with CSV export
│   └── ResultErrorBoundary # Catches Plotly render errors; shows fallback card
├── context/
│   └── AuthContext.tsx     # useAuth hook: token in memory, login/logout/refreshToken
├── hooks/
│   └── useSessionWebSocket # WebSocket client: emits typed status events
├── pages/
│   ├── LoginPage           # Username/password form + SSO button (if AUTH_MODE != local)
│   └── ChatPage            # Full chat layout: sidebar + messages + input bar
├── admin/
│   ├── UserManagementPage  # User table, new user form, role dropdown, deactivate
│   ├── PermissionEditor    # Per-user source/table access modal
│   ├── DataSourceAdminPage # Source list, DB connection form, file upload dropzone
│   ├── KnowledgeEditorPage # File tree + Monaco editor + live preview + gap dashboard
│   └── AuditLogPage        # Filterable audit table with CSV export
└── types/index.ts          # Shared TypeScript interfaces
```

### Routing

| Path | Component | Access |
|---|---|---|
| `/login` | `LoginPage` | Public |
| `/chat` | `ChatPage` (no session) | Authenticated |
| `/chat/:sessionId` | `ChatPage` (active session) | Authenticated |
| `/admin/users` | `UserManagementPage` | Authenticated (super_admin enforced by API) |
| `/admin/sources` | `DataSourceAdminPage` | Authenticated (data_admin enforced by API) |
| `/admin/knowledge/:sourceId` | `KnowledgeEditorPage` | Authenticated |
| `/admin/audit` | `AuditLogPage` | Authenticated (super_admin enforced by API) |

`ProtectedRoute` wraps all non-login routes; it redirects to `/login` if no token is in the auth context. Role enforcement is done server-side — the frontend only hides UI elements based on role.

### Token Storage

JWT is stored in the `AuthContext` React state and also mirrored to `sessionStorage` so the Axios interceptor can attach it to every request. It is **not** stored in `localStorage`. The Axios interceptor redirects to `/login` on any 401 response.

### WebSocket Protocol

`useSessionWebSocket` connects to `ws://api/ws/sessions/:id/query` and exchanges JSON messages:

**Client → Server:**
```json
{ "question": "...", "token": "...", "clarification_answers": [...] }
```

**Server → Client events:**
```
{ "event": "thinking" }
{ "event": "clarifying", "data": { "questions": [...], "turn_id": "..." } }
{ "event": "generating" }
{ "event": "executing", "data": { "attempt": 1 } }
{ "event": "done", "data": { "turn_id": "...", "result": {...} } }
{ "event": "error", "data": { "message": "...", "error_type": "..." } }
```

The hook surfaces these as typed `status` state, allowing `ChatPage` to render live progress indicators and inline clarification cards.

### Visualization

**ChartResult** uses `react-plotly.js` with dark theme overrides. The Plotly `config` enables `displayModeBar` and `toImage` (PNG download). CSV export is generated client-side from the trace data as a `Blob` download.

**TableResult** renders `{columns, rows}` payloads. Column headers are clickable sort toggles (asc/desc). Rows are paginated at 50/page. CSV export is generated from the raw row data.

Both are wrapped in `ResultErrorBoundary` (a React class error boundary) which catches rendering failures from malformed payloads and shows a fallback card instead of crashing the page.

---

## 4. API Service

**Stack:** Python 3.11, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2.

### Application Entry (`backend/main.py`)

On startup (`lifespan`), the API runs `seed_superadmin` — if the `users` table is empty, it creates the break-glass super-admin account from `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` env vars.

### Router Map

| Prefix | Router file | Role guard |
|---|---|---|
| `/auth` | `routers/auth.py` | Public (login/logout/SSO) |
| `/users` | `routers/users.py` | `super_admin` |
| `/users/{id}/permissions` | `routers/users.py` | `data_admin` |
| `/sources` | `routers/data_sources.py` | `data_admin` (create/delete), all (read) |
| `/knowledge` | `routers/knowledge.py` | `data_admin` |
| `/sessions` | `routers/sessions.py` | Authenticated |
| `/ws/sessions/{id}/query` | `routers/sessions.py` | Authenticated (token in WS message) |
| `/audit` | `routers/audit.py` | `super_admin` |

### Services

```
backend/services/
├── auth_service.py        # bcrypt hashing, JWT encode/decode, seed_superadmin
├── user_service.py        # create/list/patch/deactivate users
├── permission_service.py  # assign source access, assign table restrictions, query permitted tables
├── data_source_manager.py # connect/disconnect/list sources; schema extraction; caching
├── knowledge_service.py   # read/write/list knowledge files; frontmatter parsing
├── embedding_service.py   # embed chunks and questions; pgvector retrieval for RAG path
├── token_estimator.py     # token counting (tiktoken / character heuristic)
├── context_strategy.py    # choose FULL / RAG / MULTI_PASS based on estimated token budget
├── code_generation.py     # Claude API call, history assembly, pattern scanner, table validator
├── query_pipeline.py      # turn lifecycle orchestrator (thinking → execute → save → audit)
├── session_service.py     # create/list/get/rename/pin/delete sessions
├── turn_service.py        # create/update/list/get session turns; refresh execution
├── audit_service.py       # write audit records (never raises; silent on failure)
└── gap_service.py         # upsert KnowledgeGapSignal records
```

### Dependency Injection

`backend/dependencies.py` provides `get_current_user` — a FastAPI dependency that:
1. Extracts the Bearer token from the `Authorization` header.
2. Decodes it with `jose.jwt.decode`.
3. Fetches the `User` row from PostgreSQL.
4. Raises `401` if token is invalid or user is inactive.

All protected routes declare `current_user: User = Depends(get_current_user)`.

---

## 5. Query Pipeline

The query pipeline (`query_pipeline.py`) orchestrates the full turn lifecycle. It is invoked by the WebSocket handler and streams status events back to the client.

### Pipeline Flow

```
WebSocket receives {question, token}
           │
           ▼
  Validate session ownership
  Load permitted tables for (user, source)
  Extract + filter schema by permissions
  Load prior turn history
  Create turn record in DB
           │
           ▼
  ┌────────────────────────────────────────────┐
  │              GENERATION LOOP (max 3)       │
  │                                            │
  │  1. emit: thinking                         │
  │  2. Assemble prompt:                       │
  │       • knowledge context (see §6)         │
  │       • permission-filtered schema         │
  │       • question history (no result data)  │
  │       • current question                   │
  │       • prior code + error (if retry)      │
  │  3. Call Claude API                        │
  │  4. Parse thinking block                   │
  │                                            │
  │  ┌─ if CLARIFICATION REQUEST ─────────┐   │
  │  │  Classify: scope vs knowledge_gap  │   │
  │  │  If gap → upsert GapSignal         │   │
  │  │  emit: clarifying                  │   │
  │  │  return (wait for user answers)    │   │
  │  └────────────────────────────────────┘   │
  │                                            │
  │  5. Extract code from response             │
  │  6. Scan for dangerous patterns            │
  │     → if blocked: audit + emit error       │
  │  7. Validate table references              │
  │     → if violated: audit + emit error      │
  │  8. emit: executing                        │
  │  9. HTTP POST to execution service         │
  │  10. On execution error: retry (loop)      │
  │  11. On success: break                     │
  └────────────────────────────────────────────┘
           │
           ▼
  Save result to SessionTurn (result_cache, result_type, data_snapshot_at)
  Auto-title session from first question
  Audit: query_completed
  emit: done
```

### History Assembly

Prior turns are passed as **questions and clarification Q&A only** — never result data, chart payloads, or generated code. This ensures data values never reach the Anthropic API.

If history exceeds 10,000 tokens, the oldest turns are summarised into a paragraph and the last 10 turns are kept verbatim.

### Clarification Classification

The pipeline inspects each clarification question for keywords (`define`, `mean`, `what is`, `how is`). Questions that appear to request domain knowledge the system lacks are classified as **knowledge gaps** and recorded via `gap_service.record_gap_signal`. These surface in the admin Knowledge Gap Dashboard.

Questions that can be answered by the user (e.g., "which time period?") are classified as **scope questions** and presented inline.

### Refresh (no LLM)

`POST /sessions/:id/turns/:turnId/refresh` re-executes the stored `generated_code` against current data without an LLM call. If the execution fails due to a schema change (`error_type: "schema_change"`), the frontend offers two recovery paths:
- **View original result** — restore the cached payload
- **Re-ask** — trigger the full pipeline with the same question against the current schema

---

## 6. Knowledge System

### File Structure

```
knowledge/
├── global.md                            # Layer 1: always included
└── sources/<source-id>/
    ├── overview.md                      # Layer 2: always included when source is active
    ├── domains/<domain-name>.md         # Layer 3: domain groupings
    ├── tables/<table-name>.md           # Layer 4: per-table annotations
    └── examples/<topic>.md             # Few-shot examples
```

Files use YAML frontmatter to declare layer type and scope. The Monaco editor (with live Markdown preview) is the authoring interface.

### Context Budget Strategy

At query time, `context_strategy.py` estimates the token cost of all relevant knowledge layers and selects a strategy:

| Estimated tokens | Strategy | Behaviour |
|---|---|---|
| < 20,000 | **FULL** | Inject all relevant layers in one LLM call |
| 20,000–80,000 | **RAG** | Embed knowledge chunks; retrieve top-K by similarity to question + all table annotations for matched tables |
| > 80,000 | **MULTI_PASS** | Pass 1: layer 1/2 + domain summaries → LLM identifies needed tables; Pass 2: fetch detailed layer 4 chunks + generate code |

Relevance for RAG and MULTI_PASS is determined by a keyword-match scorer and semantic embedding retrieval (`embedding_service.py` using `sentence-transformers` + pgvector).

### Knowledge Gap Signals

When a clarification question is classified as a `knowledge_gap`, the system upserts a `KnowledgeGapSignal` record (incrementing frequency, updating `last_seen_at`). The **Knowledge Gap Dashboard** in the admin panel surfaces these sorted by frequency, letting data admins prioritise curriculum improvements.

---

## 7. Code Execution Engine

**Stack:** Python 3.11-slim FastAPI service, runs as non-root user `executor`.

### Import Allowlist

`execution/importer.py` installs a custom import hook that intercepts all `import` calls at runtime. Any module not in the allowlist raises `ImportError`:

```
pandas, numpy, duckdb, plotly, plotly.graph_objects,
datetime, math, json, re, collections, pyarrow
```

### Resource Limits

| Limit | Mechanism | Default |
|---|---|---|
| Execution timeout | `signal.alarm(TIMEOUT)` via `SIGALRM` | 30 seconds |
| Memory | `resource.setrlimit(RLIMIT_AS)` | 512 MB |

### Execution Flow

```
POST /execute { code, data_source_config }
  │
  ├── setrlimit (memory cap)
  ├── signal.alarm (timeout)
  ├── exec(compile(code)) in isolated namespace
  │   └── namespace contains _ds_config (connection params)
  │
  ├── inspect namespace["result"]
  │   ├── plotly.Figure → serialize to JSON → { type: "chart", data: ... }
  │   ├── pd.DataFrame  → { type: "table", data: {columns, rows} }
  │   └── None          → { type: "empty" }
  │
  └── on exception:
      ├── TimeoutError   → { type: "error", error_type: "timeout" }
      ├── MemoryError    → { type: "error", error_type: "memory" }
      ├── ImportError    → { type: "error", error_type: "import" }
      └── Other          → { type: "error", error_type: "schema_change" | "runtime" }
```

Schema-change errors are detected by keyword matching on the error message (`column`, `table`, `does not exist`, `no such`) and surface with `error_type: "schema_change"` so the frontend can offer the correct recovery UI.

---

## 8. Data Model

All application state is stored in a single PostgreSQL instance (pgvector extension for vector embeddings).

### Entity Relationship

```
User
 ├── UserSourcePermission (many)   — which sources & tables a user can access
 ├── ChatSession (many)            — scoped to one data source
 │    └── SessionTurn (many)       — one turn per Q&A exchange
 └── AuditLog (many)

DataSource
 ├── UserSourcePermission (many)
 ├── ChatSession (many)
 └── KnowledgeGapSignal (many)
```

### Tables

**`users`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `email` | VARCHAR(255) UNIQUE | |
| `username` | VARCHAR(100) UNIQUE | |
| `hashed_password` | VARCHAR(255) NULLABLE | NULL for pure SSO users |
| `role` | ENUM | `super_admin`, `data_admin`, `user` |
| `is_active` | BOOLEAN | Soft-delete via deactivation |
| `created_at` | TIMESTAMPTZ | |

**`data_sources`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | VARCHAR(255) | |
| `type` | ENUM | `postgres`, `mysql`, `sqlite`, `csv`, `json`, `parquet` |
| `connection_config` | JSON | Encrypted before storage |
| `created_by` | UUID FK → users | |
| `created_at` | TIMESTAMPTZ | |

**`user_source_permissions`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `source_id` | UUID FK → data_sources | |
| `permitted_tables` | JSON NULLABLE | `null` = all tables; array = restricted subset |

**`chat_sessions`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `source_id` | UUID FK → data_sources | Locked at creation |
| `title` | VARCHAR(255) | Auto-set from first question |
| `is_pinned` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |
| `last_active_at` | TIMESTAMPTZ | Updated on every new turn |

**`session_turns`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `session_id` | UUID FK → chat_sessions | |
| `sequence` | INTEGER | Turn order within session |
| `question` | TEXT | |
| `clarification_qa` | JSON NULLABLE | `[{question, answer}]` — ephemeral clarification pairs |
| `thinking` | TEXT NULLABLE | LLM reasoning block |
| `generated_code` | TEXT NULLABLE | Final executable code |
| `result_cache` | JSON NULLABLE | Last successful execution result payload |
| `result_type` | ENUM NULLABLE | `chart`, `table`, `clarification`, `error`, `empty` |
| `data_snapshot_at` | TIMESTAMPTZ NULLABLE | When `result_cache` was last populated |
| `executed_at` | TIMESTAMPTZ NULLABLE | |

**`audit_logs`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `event_type` | ENUM | See §10 |
| `user_id` | UUID FK NULLABLE | |
| `source_id` | UUID FK NULLABLE | |
| `details` | JSON | Event-specific payload |
| `created_at` | TIMESTAMPTZ | |

**`knowledge_gap_signals`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `source_id` | UUID FK → data_sources | |
| `question_text` | TEXT | The unanswered clarification question |
| `frequency` | INTEGER | Incremented on each occurrence |
| `last_seen_at` | TIMESTAMPTZ | |
| `resolved` | BOOLEAN | Marked resolved by admin |

---

## 9. Authentication & Authorization

### Local Auth (default)

1. `POST /auth/login` accepts `{username, password}`.
2. `auth_service.authenticate_user` verifies bcrypt hash.
3. Returns a signed JWT containing `{sub: user_id, role, exp}`.
4. All subsequent requests attach `Authorization: Bearer <token>`.

### SSO (OIDC / SAML)

Set `AUTH_MODE=oidc` or `AUTH_MODE=saml` and provide provider credentials. The API uses `authlib` to implement:
- `GET /auth/sso/login` → redirect to provider
- `GET /auth/sso/callback` → exchange code for token, upsert user, return JWT

The local login form remains active as a break-glass path regardless of `AUTH_MODE`.

### Role Enforcement

Roles are embedded in the JWT and re-validated against the DB on each request via `get_current_user`. Router-level guards check:

```python
if current_user.role not in (UserRole.super_admin,):
    raise HTTPException(403)
```

### Table-Level Permission Enforcement

Two layers:

1. **Schema filtering at prompt build time** — `permission_service.get_permitted_tables` returns the user's allowed table list. `DataSourceManager.get_filtered_schema` strips all other tables from the schema before it is injected into the LLM prompt. The LLM cannot reason about tables it has never seen.

2. **Post-generation validation** — `code_generation.validate_table_permissions` parses table name references from the generated code (regex over `FROM`, `JOIN`, DuckDB `read_csv`/`read_parquet` calls). Any reference to a non-permitted table is rejected before execution, and the violation is written to the audit log with `event_type: code_blocked`.

---

## 10. Audit Logging

`audit_service.AuditService.log` is a fire-and-forget coroutine that writes to `audit_logs`. It **never raises** — a failed audit write is logged to stderr but never propagates to block the user action.

### Event Types

| Category | Events |
|---|---|
| **Query** | `query_submitted`, `code_generated`, `code_blocked`, `query_completed`, `query_failed` |
| **Auth** | `login_success`, `login_failed`, `logout`, `sso_login` |
| **Admin** | `user_created`, `user_role_changed`, `source_connected`, `source_deleted`, `permission_granted`, `permission_revoked`, `knowledge_updated` |

`GET /audit` supports filters: `user_id`, `event_type`, `source_id`, `date_from`, `date_to`. `GET /audit/export` returns CSV. Both are restricted to `super_admin`.

---

## 11. Data Flow: End-to-End Query

A complete query — from the user typing a question to seeing a chart — follows this path:

```
1. User types question → presses Enter
   ChatPage.handleSend()

2. WebSocket client sends:
   { question, token }

3. API: WS handler validates token + session ownership

4. QueryPipeline.stream_turn() begins:
   a. Load permitted tables (permission_service)
   b. Extract schema from data source
   c. Filter schema to permitted tables only
   d. Load turn history from DB (questions + clarification Q&A only)
   e. Create new SessionTurn record

5. emit: { event: "thinking" }
   Frontend shows spinner

6. context_strategy.build_context_plan():
   - Estimate token cost of knowledge layers
   - Choose FULL / RAG / MULTI_PASS
   - Assemble relevant knowledge files

7. code_generation.generate_code():
   - Build prompt: [knowledge] + [schema] + [history] + [question]
   - Call claude-sonnet-4-6 via Anthropic SDK
   - Parse <thinking> block
   - Detect: clarification request OR executable code

   If CLARIFICATION:
     a. Classify: scope vs knowledge_gap
     b. Record gap signals if knowledge_gap
     c. emit: { event: "clarifying", data: { questions, turn_id } }
     d. Pipeline suspends — waits for user to submit answers
     e. User submits answers via WebSocket
     f. Pipeline resumes from step 6 with answers attached

8. Safety scan: regex check for dangerous patterns
   → on failure: audit code_blocked + emit error

9. Table permission check: parse table refs from code
   → on failure: audit code_blocked + emit error

10. emit: { event: "executing" }
    Frontend shows spinner

11. HTTP POST execution_service/execute:
    { code, data_source_config }

12. Execution service:
    - setrlimit (512MB)
    - signal.alarm (30s)
    - exec(code) in isolated namespace
    - Detect result type (Figure / DataFrame / None)
    - Return: { type: "chart"|"table"|"empty"|"error", data: ... }

    On error: pipeline retries up to 2x with error context injected into prompt

13. On success:
    a. Save result_cache + result_type + data_snapshot_at to SessionTurn
    b. Auto-title session from first question
    c. audit: query_completed
    d. emit: { event: "done", data: { turn_id, result } }

14. Frontend:
    a. Re-fetches turns from /sessions/:id/turns
    b. TurnMessage renders:
       - Thinking block (expanded on turn 1, collapsed 2+)
       - ChartResult or TableResult
       - StalenessBar with "Last updated: N minutes ago"
       - Code block (expanded on turn 1, collapsed 2+)
```

---

## 12. Security Model

### Attack Surface & Mitigations

| Threat | Mitigation |
|---|---|
| **SQL injection via LLM prompt** | Schema filtering: LLM never sees restricted tables. Code validation checks table references before execution. |
| **Prompt injection via question** | User question is passed as content, not as system instructions. The system prompt is admin-controlled only. |
| **Dangerous code execution** | Regex scan for `os`, `sys`, `subprocess`, `eval`, `exec`, `open`, `__import__`, `__builtins__`, etc. before execution. |
| **Import abuse in execution** | Custom import hook blocks everything outside the allowlist at runtime. |
| **Resource exhaustion** | 30s timeout via `SIGALRM`; 512MB memory via `RLIMIT_AS`. |
| **Container escape** | Execution container: non-root user, `cap_drop: ALL`, `no-new-privileges`, no external network. |
| **Credential leakage to LLM** | Data source `connection_config` is encrypted at rest. Result data is never sent to the LLM — only questions and clarification Q&A are included in history. |
| **Token theft** | JWT stored in memory (`AuthContext` React state + `sessionStorage`), not `localStorage`. Expires after configurable TTL. |
| **SSO lockout** | Local super-admin account always available as break-glass regardless of `AUTH_MODE`. |
| **Audit tampering** | `super_admin`-only read access; audit writes are append-only (no update/delete endpoint). |

### Defense in Depth for Table Permissions

```
Layer 1: Schema filtering
  The LLM prompt only contains schema for permitted tables.
  The LLM cannot reference what it cannot see.

Layer 2: Post-generation validation
  Generated code is parsed for table references before execution.
  Violations are blocked and audit-logged.

Layer 3 (optional): DB-level roles
  Admins may configure DB users with restricted grants per source.
  Not required by the application but compatible as a third layer.
```

---

## 13. Configuration Reference

All configuration is loaded from environment variables via `backend/config.py` (Pydantic Settings).

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic Claude API key |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://daitaview:daitaview@db:5432/daitaview` | PostgreSQL async connection string |
| `SECRET_KEY` | Yes | `change-me` | JWT HMAC signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `480` | JWT lifetime |
| `AUTH_MODE` | No | `local` | `local`, `oidc`, or `saml` |
| `SSO_PROVIDER_URL` | If SSO | — | OIDC issuer / SAML metadata URL |
| `SSO_CLIENT_ID` | If SSO | — | OAuth2 client ID |
| `SSO_CLIENT_SECRET` | If SSO | — | OAuth2 client secret |
| `SSO_REDIRECT_URI` | If SSO | — | Callback URL |
| `SUPERADMIN_EMAIL` | No | `admin@example.com` | Seeded on first start |
| `SUPERADMIN_PASSWORD` | No | `change-me-immediately` | Seeded on first start |
| `EXECUTION_SERVICE_URL` | No | `http://execution:8001` | Internal execution service URL |
| `EXECUTION_TIMEOUT_SECONDS` | No | `30` | Per-query timeout |
| `EXECUTION_MEMORY_LIMIT_MB` | No | `512` | Execution container memory cap |
| `MAX_UPLOAD_SIZE_MB` | No | `500` | Max file upload size |
| `UPLOADS_PATH` | No | `/app/uploads` | File source storage path |
| `KNOWLEDGE_PATH` | No | `/app/knowledge` | Knowledge file storage path |
| `VECTOR_STORE_PATH` | No | `/app/vector_store` | Embedding vector store path |

### LLM Model

The API uses `claude-sonnet-4-6` (configured in `code_generation.py`). The model is called via the official `anthropic` Python SDK with extended thinking enabled to produce the reasoning block before code generation.
