## 1. Project Setup

- [x] 1.1 Initialize backend Python project: `pyproject.toml` with FastAPI, anthropic, pandas, duckdb, plotly, sqlalchemy, alembic, asyncpg, uvicorn, python-jose, passlib, bcrypt, authlib, sentence-transformers dependencies
- [x] 1.2 Initialize frontend React + Vite project: install `react-plotly.js`, `plotly.js`, `axios`, `react-query`, `@monaco-editor/react`, `react-router-dom`
- [x] 1.3 Create project directory structure: `backend/`, `backend/services/`, `backend/routers/`, `backend/models/`, `backend/migrations/`, `frontend/src/`, `execution/`, `knowledge/`
- [x] 1.4 Add `.env.example` with: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `SECRET_KEY`, `AUTH_MODE` (local/oidc/saml), `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_REDIRECT_URI`, `SSO_PROVIDER_URL`
- [x] 1.5 Add `docker-compose.yml` with services: `frontend`, `api`, `execution`, `db` (PostgreSQL), `vector-store` (pgvector or Chroma)
- [x] 1.6 Add `execution/Dockerfile`: Python image with allowlisted packages only (pandas, numpy, duckdb, plotly, datetime, math, json, re, collections), no network access, non-root user
- [x] 1.7 Initialize Alembic for database migrations: `alembic init`, configure to use `DATABASE_URL` from env

## 2. Database Models & Migrations

- [x] 2.1 Define `User` model: id, email, username, hashed_password, role (super_admin/data_admin/user), is_active, created_at
- [x] 2.2 Define `DataSource` model: id, name, type (postgres/mysql/sqlite/csv/json/parquet), connection_config (encrypted JSON), created_by, created_at
- [x] 2.3 Define `UserSourcePermission` model: user_id, source_id, permitted_tables (JSON array, null = all tables)
- [x] 2.4 Define `ChatSession` model: id, user_id, source_id, title, is_pinned, created_at, last_active_at
- [x] 2.5 Define `SessionTurn` model: id, session_id, sequence, question, clarification_qa (JSON), thinking, generated_code, result_cache (JSON), result_type (chart/table/clarification/error), data_snapshot_at, executed_at
- [x] 2.6 Define `AuditLog` model: id, event_type (query/admin/auth), user_id, source_id, details (JSON), created_at
- [x] 2.7 Define `KnowledgeGapSignal` model: id, source_id, question_text, frequency, last_seen_at, resolved (bool)
- [x] 2.8 Generate and apply initial Alembic migration for all models

## 3. Auth & User Management

- [x] 3.1 Implement `AuthService` in `backend/services/auth_service.py`: hash password, verify password, create JWT access token, decode token
- [x] 3.2 Implement local auth endpoints: `POST /auth/login` (username + password → JWT), `POST /auth/logout`
- [x] 3.3 Implement SSO flow: read `AUTH_MODE` from env; if `oidc` or `saml`, wire OIDC/SAML redirect + callback endpoints using authlib; local login always available as break-glass
- [x] 3.4 Add `get_current_user` FastAPI dependency that validates JWT and returns the user; use on all protected routes
- [x] 3.5 Implement `UserService` in `backend/services/user_service.py`: create user, list users, update role, deactivate user
- [x] 3.6 Add user management router `backend/routers/users.py`: `GET /users`, `POST /users`, `PATCH /users/{id}`, `DELETE /users/{id}` — super_admin only
- [x] 3.7 Implement permission service `backend/services/permission_service.py`: assign source access, assign table restrictions, get permitted tables for (user, source)
- [x] 3.8 Add permission endpoints: `POST /users/{id}/permissions`, `GET /users/{id}/permissions`, `DELETE /users/{id}/permissions/{source_id}` — data_admin only

## 4. Data Source Manager

- [x] 4.1 Implement `DataSourceManager` in `backend/services/data_source_manager.py`: connect, disconnect, list, get by id; encrypt connection config before saving
- [x] 4.2 Implement database connector: test SQLAlchemy connection for PostgreSQL/MySQL/SQLite on save; raise descriptive error on failure
- [x] 4.3 Implement file source connector: accept CSV/JSON/Parquet upload to `uploads/<source_id>/`, register in DuckDB, persist metadata to DB
- [x] 4.4 Implement schema extractor: read table names, column names, data types, and 5 sample rows from any connected source
- [x] 4.5 Implement permission-filtered schema view: given (user, source), return only the tables the user is permitted to see — restricted tables omitted entirely
- [x] 4.6 Add schema caching layer: cache extracted schema in memory keyed by (source_id, schema_hash); invalidate on refresh
- [x] 4.7 Add data source router `backend/routers/data_sources.py`: `POST /sources`, `GET /sources`, `GET /sources/{id}/schema`, `DELETE /sources/{id}`, `POST /sources/{id}/refresh-schema`, `POST /sources/upload` — data_admin for create/delete, all users for read

## 5. Knowledge Management

- [x] 5.1 Implement knowledge file storage: enforce the directory structure `knowledge/global.md`, `knowledge/sources/<id>/overview.md`, `knowledge/sources/<id>/domains/<name>.md`, `knowledge/sources/<id>/tables/<name>.md`, `knowledge/sources/<id>/examples/<topic>.md`
- [x] 5.2 Implement `KnowledgeService` in `backend/services/knowledge_service.py`: read, write, list, delete knowledge files; parse frontmatter for layer type and scope metadata
- [x] 5.3 Add knowledge router `backend/routers/knowledge.py`: `GET /knowledge/{source_id}` (file tree), `GET /knowledge/{source_id}/file` (read file), `PUT /knowledge/{source_id}/file` (write file), `DELETE /knowledge/{source_id}/file` — data_admin only
- [x] 5.4 Implement token estimator: count approximate tokens for a knowledge layer set using tiktoken or character-based heuristic
- [x] 5.5 Implement context strategy selector: given (question, source, user_permissions), estimate token budget and return strategy (`full`, `rag`, `multi_pass`) with the relevant knowledge file paths
- [x] 5.6 Implement embedding service `backend/services/embedding_service.py`: embed knowledge chunks and question using sentence-transformers; store chunk embeddings in vector store; retrieve top-K for RAG path
- [x] 5.7 Implement knowledge gap signal recorder: when a clarification is classified as `knowledge_gap` type, upsert a `KnowledgeGapSignal` record (increment frequency, update last_seen_at)
- [x] 5.8 Add gap dashboard endpoint: `GET /knowledge/{source_id}/gaps` — returns unresolved gap signals sorted by frequency; `POST /knowledge/{source_id}/gaps/{id}/resolve` marks resolved — data_admin only

## 6. LLM Code Generation Service

- [x] 6.1 Implement `CodeGenerationService` in `backend/services/code_generation.py` using the `anthropic` SDK
- [x] 6.2 Implement prompt builder: assemble (1) knowledge curriculum from context strategy, (2) permission-filtered schema, (3) question history (questions + clarification Q&A only, never result data), (4) current question
- [x] 6.3 Implement question history assembler: collect prior turns' questions and clarification Q&A from the session; if history exceeds 10k tokens, summarise oldest turns into a paragraph and keep last 10 verbatim
- [x] 6.4 Implement thinking phase parser: extract the `<thinking>` block from the LLM response; detect whether the output is a clarification request or executable code
- [x] 6.5 Implement clarification classifier: determine if a clarification question is `scope` type (user can answer) or `knowledge_gap` type (admin should fill); route accordingly and record gap signals
- [x] 6.6 Implement code extractor: strip markdown fences from code blocks in LLM response
- [x] 6.7 Implement dangerous-pattern scanner: reject code containing `os`, `sys`, `subprocess`, `eval`, `exec`, `open`, `__import__`, `__builtins__`; log violation to audit log
- [x] 6.8 Implement table reference validator: parse table names from generated code; reject and log if any referenced table is not in the user's permitted set
- [x] 6.9 Implement retry loop: on execution failure, re-call LLM with original prompt + prior code + error message, up to 2 retries

## 7. Code Execution Engine (Docker)

- [x] 7.1 Implement execution API in `execution/main.py`: FastAPI app that accepts `POST /execute` with `{code, data_source_config}`, runs code in restricted environment, returns structured result
- [x] 7.2 Enforce import allowlist inside execution container: intercept imports at runtime; raise `ImportError` for anything not in allowlist (pandas, numpy, duckdb, plotly, datetime, math, json, re, collections)
- [x] 7.3 Enforce resource limits: 30-second execution timeout via `signal.alarm`; 512MB memory limit via `resource.setrlimit`
- [x] 7.4 Implement result serializer: detect `result` variable type — Plotly figure → serialize to JSON dict with `type: "chart"`; DataFrame → convert to `{columns, rows}` with `type: "table"`; neither → return warning with `type: "empty"`
- [x] 7.5 Handle schema-change errors distinctly: catch `ColumnNotFound` / `TableNotFound` errors and return them with `error_type: "schema_change"` so the API layer can surface the correct recovery UI
- [x] 7.6 Write unit tests for execution engine: success (chart), success (table), timeout, memory exceeded, blocked import, schema-change error

## 8. Query Pipeline & Session Management

- [x] 8.1 Implement `SessionService` in `backend/services/session_service.py`: create session (with source_id lock), get, list by user, rename, pin/unpin, delete
- [x] 8.2 Implement `TurnService` in `backend/services/turn_service.py`: create turn, update turn (store code + result_cache + data_snapshot_at), list turns for session, get turn by id
- [x] 8.3 Add session router `backend/routers/sessions.py`: `POST /sessions`, `GET /sessions`, `GET /sessions/{id}`, `PATCH /sessions/{id}` (rename/pin), `DELETE /sessions/{id}`, `GET /sessions/{id}/turns`
- [x] 8.4 Add refresh endpoint `POST /sessions/{id}/turns/{turn_id}/refresh`: re-execute `generated_code` from the stored turn against current data (no LLM call); update `result_cache` and `data_snapshot_at`; return `error_type: "schema_change"` if execution fails due to schema mismatch
- [x] 8.5 Add refresh-all endpoint `POST /sessions/{id}/refresh`: call refresh on every turn in the session sequentially
- [x] 8.6 Implement `QueryPipeline` orchestrator in `backend/services/query_pipeline.py`: thinking phase → clarification check → knowledge context assembly → code generation → safety scan → table permission check → execution → result packaging → turn save → audit log write
- [x] 8.7 Add WebSocket endpoint `WS /ws/sessions/{id}/query`: accepts `{question}`; streams status events `thinking`, `clarifying`, `generating`, `executing`, `done`, `error`; handles clarification round-trip inline
- [x] 8.8 Add request validation: reject empty questions; validate session exists and belongs to current user; validate source is still accessible

## 9. Audit Logging

- [x] 9.1 Implement `AuditService` in `backend/services/audit_service.py`: write audit record; never raise — log errors silently so audit failure never blocks a user action
- [x] 9.2 Hook audit logging into `QueryPipeline`: log `query_submitted`, `code_generated`, `code_blocked` (safety/permission violations), `query_completed`, `query_failed`
- [x] 9.3 Hook audit logging into auth endpoints: log `login_success`, `login_failed`, `logout`, `sso_login`
- [x] 9.4 Hook audit logging into admin actions: log `user_created`, `user_role_changed`, `source_connected`, `source_deleted`, `permission_granted`, `permission_revoked`, `knowledge_updated`
- [x] 9.5 Add audit router `backend/routers/audit.py`: `GET /audit` with filters (user_id, event_type, date range, source_id); `GET /audit/export` returns CSV — super_admin only

## 10. Frontend — App Shell & Auth

- [x] 10.1 Implement `LoginPage` component: username + password form; on success store JWT in memory (not localStorage); handle SSO redirect button if `AUTH_MODE != local`
- [x] 10.2 Implement auth context `useAuth`: stores current user + token; provides `login`, `logout`, `refreshToken`; redirects to login on 401
- [x] 10.3 Implement `ProtectedRoute` wrapper: redirect to login if unauthenticated
- [x] 10.4 Set up `react-router-dom` routes: `/login`, `/chat`, `/chat/:sessionId`, `/admin/users`, `/admin/sources`, `/admin/knowledge/:sourceId`, `/admin/audit`
- [x] 10.5 Implement top nav bar: current user display, logout button, admin link (visible to admin roles only)

## 11. Frontend — Session Sidebar & Chat UI

- [x] 11.1 Implement `SessionSidebar` component: grouped session list (Today / Yesterday / Last 7 days / Older), pinned sessions at top, each entry shows title + source name + relative timestamp
- [x] 11.2 Implement session context menu: rename (inline edit on double-click or menu), pin/unpin, delete with confirmation
- [x] 11.3 Implement `NewChatModal`: lists data sources the user can access; "Start Chat" creates session and navigates to `/chat/:sessionId`; shows "no sources" message if user has no permissions
- [x] 11.4 Implement `ChatPage` layout: sidebar + main chat area + persistent source name in session header + input bar at bottom
- [x] 11.5 Implement `useSessionWebSocket` hook: connects to `WS /ws/sessions/:id/query`; emits typed events (`thinking`, `clarifying`, `generating`, `executing`, `done`, `error`); handles clarification round-trip
- [x] 11.6 Implement `TurnMessage` component: user question bubble; AI response with thinking block (expanded turn 1, collapsed turn 2+), result card, code block (expanded turn 1, collapsed turn 2+)
- [x] 11.7 Implement `ClarificationCard` component: renders structured clarification questions with radio options or text input inline; submit sends answers back through WebSocket to resume pipeline
- [x] 11.8 Implement `StalenessBar`: banner shown when most recent result in session is older than 1 hour; "Refresh all" button calls `POST /sessions/:id/refresh`
- [x] 11.9 Implement staleness badge on each result card: "Last updated: [timestamp]" + Refresh button; on click calls `POST /sessions/:id/turns/:turnId/refresh`
- [x] 11.10 Implement schema-change error state on result card: shows error message + "View original result" (restores cached payload) + "Re-ask" (triggers new full pipeline turn with same question)

## 12. Frontend — Visualization Renderer

- [x] 12.1 Implement `ChartResult` component: renders Plotly figure from JSON payload using `react-plotly.js` with pan, zoom, hover tooltips, and PNG download enabled
- [x] 12.2 Implement `TableResult` component: sortable column headers (asc/desc toggle), 50 rows per page, pagination controls
- [x] 12.3 Implement CSV export button on both chart and table results: generate Blob from row data and trigger browser download
- [x] 12.4 Implement `ResultErrorBoundary`: catches rendering errors from malformed Plotly JSON and shows a fallback error card instead of crashing

## 13. Frontend — Admin Panel

- [x] 13.1 Implement `UserManagementPage`: table of users with role badge; "New User" form (email, username, password, role); role change dropdown; deactivate button
- [x] 13.2 Implement `PermissionEditor` modal: per-user, shows list of sources with toggle (full access / table-level / no access); table-level selector shows checkboxes per table
- [x] 13.3 Implement `DataSourceAdminPage`: list connected sources; "Add Database" form (type, host, port, db, user, password); file upload dropzone; "Refresh Schema" + delete per source
- [x] 13.4 Implement `KnowledgeEditorPage`: file tree on left (global.md + per-source hierarchy); Monaco editor in centre with markdown syntax highlighting; live preview on right; save button calls `PUT /knowledge/:sourceId/file`
- [x] 13.5 Implement `KnowledgeGapDashboard` section on KnowledgeEditorPage: list of unresolved gap signals sorted by frequency; "Add to KB" shortcut opens editor at relevant file; "Dismiss" marks resolved
- [x] 13.6 Implement `AuditLogPage`: filterable table (by user, event type, date range, source); "Export CSV" button; read-only, super_admin only

## 14. Integration & Polish

- [x] 14.1 Add `SUPERADMIN_EMAIL` + `SUPERADMIN_PASSWORD` env vars; on first `docker-compose up`, seed the super-admin account via Alembic `post-migrate` hook if no users exist
- [x] 14.2 Add end-to-end test: upload a CSV source → add knowledge → ask a bar chart question → verify chart renders and staleness badge shows
- [x] 14.3 Add end-to-end test: multi-turn session — ask follow-up question that references previous question, verify LLM resolves it correctly
- [x] 14.4 Add end-to-end test: table permission — user without access to a table asks a question about it, verify safe error returned and audit log records the violation
- [x] 14.5 Add `README.md`: setup instructions, `docker-compose up` quickstart, env var reference, first-run admin setup, adding a data source, authoring knowledge
- [x] 14.6 Verify all Docker services build and start cleanly; confirm execution container has no network access and correct resource limits applied
