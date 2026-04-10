## Why

Companies have data trapped in databases and files that most employees can't access without SQL or Python skills. This tool solves that by letting users ask questions in plain English — but unlike generic AI query tools, it puts the admin in control: admins teach the system company-specific data knowledge (business rules, table semantics, domain context) before any query runs, ensuring the LLM generates accurate, company-aware code rather than generic guesses. It is a company-level platform with user management, strict data source access control, and full audit logging.

## What Changes

- Introduce a chat-style natural language query interface with a thinking-then-clarify-then-generate pipeline
- Add an admin-curated knowledge management system: a four-layer curriculum (global → source → domain → table) that admins maintain via a markdown editor
- Add an LLM code generation pipeline that uses the knowledge curriculum as context, with a dynamic context budget strategy (full dump / semantic RAG / multi-pass agentic) based on knowledge base size
- Add a thinking phase where the LLM reasons about the question before writing code, and asks structured clarification questions when knowledge is insufficient
- Add a Docker-based sandboxed code execution service
- Add user and access management: username/password auth by default, SSO configurable via `.env`, with source-level and table-level permission control
- Add audit logging for all query events, admin actions, and access events
- Add visualization rendering (charts and tables) with CSV export
- Add query history with replay

## Capabilities

### New Capabilities
- `nl-query-interface`: Chat UI with thinking phase display, structured clarification flow, generated code visibility, and result rendering
- `knowledge-management`: Admin curriculum editor — four-layer markdown-based knowledge base (global, source, domain, table), knowledge gap detection from clarification patterns, admin dashboard surfacing frequent gaps
- `llm-code-generation`: LLM pipeline with dynamic context budget strategy (full / RAG / multi-pass), schema filtering by user permissions, structured thinking phase, and retry-with-error-context loop
- `code-execution-engine`: Docker-based sandboxed execution service with import allowlist, resource limits, and structured result serialization
- `data-source-manager`: Connection management for PostgreSQL, MySQL, SQLite, CSV, JSON, Parquet — with schema extraction, caching, and per-user table-level permission filtering at prompt-build time
- `user-access-management`: User accounts, roles (super admin / data admin / business user), source-level and table-level permission assignment, username/password auth with optional SSO via `.env`
- `visualization-renderer`: Auto chart type selection, interactive Plotly rendering, paginated table grid, CSV export
- `query-history`: Per-user query history with generated code, results, replay, and delete
- `audit-logging`: Immutable log of query events, admin actions, and authentication events — filterable and exportable by admins

### Modified Capabilities
<!-- Greenfield project — no prior capabilities exist. -->

## Impact

- **New dependencies**: `anthropic` (Claude API), `pandas`, `duckdb`, `plotly`, `sqlalchemy`, Docker (execution sandbox), FastAPI, `sentence-transformers` or equivalent for embedding (RAG path), `passlib`/`bcrypt` (auth), `python-jose` (JWT), SSO library (e.g., `python-saml`, `authlib`)
- **Frontend**: React chat UI, markdown editor (e.g., CodeMirror or Monaco), data source manager, user management panel, admin knowledge dashboard, audit log viewer
- **Backend**: FastAPI API service, Python execution container (Docker), knowledge store with embedding index, PostgreSQL for app state (users, permissions, history, audit log)
- **Security**: Table-level schema filtering before LLM prompt; generated code validated against permitted tables before execution; sandboxed Docker execution; all actions audit-logged
- **Auth**: Local username/password default; OIDC/SAML SSO enabled via `AUTH_MODE` env var; one local super-admin account always functional as break-glass regardless of SSO config
- **Deployment**: All services containerized via `docker-compose`
