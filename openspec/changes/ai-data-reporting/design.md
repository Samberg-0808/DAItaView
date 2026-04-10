## Context

DAItaView is a company-level AI data reporting platform. It allows business users to ask natural language questions and receive data visualizations — but its differentiating capability is admin-curated knowledge injection: admins teach the system company-specific data knowledge (business rules, domain context, table semantics, example queries) via a markdown editor. The LLM treats this curriculum as onboarding material, reasoning from it before generating code, and asking structured clarification questions when knowledge is insufficient.

The system is multi-user with role-based access control, source-level and table-level data permissions, SSO support, and full audit logging. All services run as Docker containers.

Stack: React frontend, FastAPI API service, Docker-based Python execution service, PostgreSQL for app state, a vector store for knowledge embeddings (RAG path), and the Anthropic Claude API.

## Goals / Non-Goals

**Goals:**
- Natural language querying with admin-curated knowledge as LLM context
- Four-layer knowledge curriculum: global → source-level → domain → table annotations
- Dynamic context budget strategy: full injection, semantic RAG, or multi-pass agentic depending on knowledge base size
- LLM thinking phase: reasons before writing code, asks structured clarifications when uncertain
- Clarification gap detection: surfaces frequently unanswered questions to admins as knowledge base improvement signals
- User management: roles, source-level and table-level permission assignment
- Auth: username/password default, SSO (OIDC/SAML) configurable via `.env`
- Sandboxed code execution in Docker with resource limits and import allowlist
- Audit logging of all query, admin, and authentication events
- Interactive visualization (Plotly charts, paginated tables, CSV export)

**Non-Goals:**
- Row-level security (source-level and table-level access only)
- Real-time or streaming data sources (batch/snapshot only)
- Scheduled or automated report delivery
- Fine-tuning or training a custom LLM
- Mobile-native clients (web only)

## Decisions

### Decision 1: Claude API for code generation
**Choice**: Anthropic Claude via the `anthropic` Python SDK.
**Rationale**: Strong Python/pandas/SQL code generation out of the box. Supports structured outputs and long context windows needed for the multi-layer knowledge injection strategy. Avoids self-hosting complexity.
**Alternative considered**: Open-source models (Llama, CodeLlama) — rejected due to hosting cost and weaker code quality for this use case.

### Decision 2: Docker container for code execution sandbox
**Choice**: Run generated code inside a dedicated Docker execution service container with a restricted Python environment, import allowlist, CPU/memory limits, and no network access.
**Rationale**: Docker provides strong process and filesystem isolation. For a company-level tool running user-influenced code against real databases, subprocess isolation (RestrictedPython) is insufficient — a container boundary is required. Latency cost is acceptable given the LLM call already dominates total query time.
**Alternative considered**: RestrictedPython + subprocess — rejected for production use; insufficient isolation for a multi-user company tool. Will not be revisited.

### Decision 3: Four-layer knowledge pyramid with dynamic context strategy
**Choice**: Organize knowledge into four layers (global, source, domain, table). At query time, select an injection strategy based on estimated token budget:
- **< 20k tokens**: Full dump — inject all relevant layers in a single LLM call.
- **20k–80k tokens**: Semantic RAG — embed knowledge chunks, retrieve top-K by similarity to question, plus all table annotations for matched tables.
- **> 80k tokens**: Multi-pass agentic — Pass 1 sends layer-1/2 + domain summaries, LLM identifies needed tables/domains; Pass 2 fetches detailed knowledge for those and generates code.

**Rationale**: A fixed strategy fails at scale. Small knowledge bases should get full context for reliability. Large ones need retrieval to stay within context/cost limits. Admin-defined domain groupings make retrieval more reliable than pure semantic search.
**Alternative considered**: Always use RAG — rejected because RAG can miss relevant context for small bases where full injection is cheap and more reliable.

### Decision 4: Table-level access enforced at schema injection, not DB role
**Choice**: When building the LLM prompt, filter the schema to only include tables the requesting user is permitted to see. Additionally, validate generated code's table references against the permitted set before execution. DB-level role enforcement is optional and not required by the application.
**Rationale**: Hiding restricted tables from the schema is the primary defense — the LLM cannot reason about tables it has never seen. Code validation is a secondary check. DB-level role management per user is operationally complex and creates a sync problem between application permissions and DB state.
**Alternative considered**: DB roles per user — useful as defense-in-depth but not mandatory for v1. Can be layered on per data source if the admin chooses.

### Decision 5: Markdown editor for admin knowledge authoring
**Choice**: Admins write knowledge in a file-per-layer markdown structure with heading conventions that indicate layer and scope. A Monaco/CodeMirror editor with live preview. Frontmatter tags the file's layer and associated source/domain/table.
**Rationale**: Markdown is familiar to technical data admins. A file-per-layer structure maps cleanly to the retrieval strategy — the system fetches files by layer type rather than parsing a monolithic document. Structured headings + frontmatter allow the system to understand scope without custom syntax.
**Structure**:
```
knowledge/
  global.md                        ← Layer 1, always included
  sources/<source-id>/
    overview.md                    ← Layer 2, always included when source is active
    domains/<domain-name>.md       ← Layer 3, retrieved by domain match
    tables/<table-name>.md         ← Layer 4, retrieved when table is referenced
    examples/<topic>.md            ← Few-shot examples, retrieved by question similarity
```

### Decision 6: Username/password default auth, SSO via .env
**Choice**: Default auth is username + bcrypt-hashed password with JWT sessions. SSO (OIDC or SAML) is enabled by setting `AUTH_MODE=oidc` or `AUTH_MODE=saml` and providing provider credentials in `.env`. One local super-admin account is always functional regardless of `AUTH_MODE` as a break-glass account.
**Rationale**: Most companies need SSO for production but local auth is essential for initial setup, development, and break-glass access. Env-based config avoids hardcoding provider details and makes it easy to switch per environment.
**Alternative considered**: SSO-only — rejected because it breaks initial onboarding and local development.

### Decision 7: LLM thinking phase before code generation
**Choice**: Before writing code, the LLM produces a structured reasoning step: identifies relevant tables, notes applicable business rules from the knowledge base, flags ambiguities, and states its intent. If confidence is low on any point, it emits structured clarification questions instead of proceeding to code. Clarification questions are typed: scope questions (user answers, ephemeral) vs knowledge gap questions (flagged to admin).
**Rationale**: A thinking-then-clarify-then-generate pipeline produces more accurate code and builds user trust (they see the reasoning). Asking before writing wrong code is better than retrying after execution failure. Surfacing knowledge gaps to admins creates a continuous improvement loop for the knowledge base.
**Alternative considered**: Generate-then-retry-on-failure only — simpler but produces incorrect results silently when the LLM makes wrong assumptions, and wastes execution cycles.

### Decision 8: PostgreSQL for all application state
**Choice**: Single PostgreSQL instance (in Docker) stores users, roles, permissions, data source configs, query history, audit log, and knowledge gap signals.
**Rationale**: Relational model fits all application state. Single service reduces operational complexity. Audit log and query history have natural relational structure (foreign keys to users, sources).
**Alternative considered**: SQLite for simplicity — rejected because PostgreSQL is needed for concurrent multi-user writes and is already in the Docker stack.

## Risks / Trade-offs

- **Multi-pass latency** → Two LLM calls + execution for large knowledge bases could take 15–30 seconds. Mitigation: stream status updates via WebSocket so users see progress; cache Pass 1 table-identification results per (question-hash, source-version).
- **Knowledge base quality determines output quality** → If admins write poor or incomplete curriculum, the LLM will produce wrong code or ask many clarifications. Mitigation: knowledge gap dashboard shows admins where curriculum is weak; example queries in the editor provide a template.
- **Docker execution cold start** → First query after container restart has extra latency. Mitigation: keep the execution container warm (always running, not spawned per query).
- **Table-level permission bypass via SQL injection in question** → A user could craft a question designed to get the LLM to reference restricted tables by name. Mitigation: schema filtering at prompt-build time is the primary guard; post-generation table reference validation is the secondary guard. Log all violations to the audit log.
- **SSO misconfiguration lockout** → If SSO is misconfigured, all users could be locked out. Mitigation: break-glass local super-admin account always bypasses SSO.
- **LLM cost at scale** → Multi-pass queries with large knowledge bases can consume significant tokens. Mitigation: context caching (Anthropic prompt caching for layer 1/2 knowledge that rarely changes), result caching by query hash.

## Migration Plan

Greenfield project — no prior state to migrate. Deployment:
1. Copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY`, database URL, and auth config
2. Run `docker-compose up --build`
3. On first start, database migrations run automatically (Alembic)
4. Create super-admin account via `docker-compose exec api python manage.py create-superadmin`
5. Admin connects first data source, authors knowledge base, creates users and assigns permissions
6. Rollback: `docker-compose down` — stateless API and execution containers; data persists in the PostgreSQL volume

### Decision 9: Chat sessions with multi-turn question-only history
**Choice**: The application is organised around persistent chat sessions. Each session is locked to one data source at creation and cannot change sources mid-session. Multi-turn context is supported by passing the full ordered list of prior questions (and clarification Q&A pairs) to the LLM — but never result data, chart payloads, or generated code. When question history exceeds 10k tokens, the oldest turns are summarised into a paragraph and the last 10 turns are kept verbatim.
**Rationale**: Locking a session to one source keeps the schema context coherent and the conversation focused. Passing questions-only (never data) preserves data privacy — result values never leave the execution environment or reach the LLM. Summarising long histories bounds context cost while preserving enough thread for the LLM to resolve follow-up references.
**Alternative considered**: Pass full turn context (questions + results + code) — rejected on privacy grounds; data values should never be sent to an external API.

### Decision 10: Results display a staleness badge; refresh re-executes stored code
**Choice**: Every query result displays a "Last updated: [timestamp]" badge and a Refresh button. On session open, if the most recent result is older than 1 hour, a banner prompts the user to refresh. Refreshing re-executes the stored generated code against the current data — it does not trigger a new LLM call. If the refresh fails because the schema has changed, the result shows an error state with two recovery options: restore the cached result, or re-run the full pipeline (LLM → code → execute) with the current schema.
**Rationale**: Users of a data reporting tool need to know whether they are looking at current data. Storing and re-executing code (not re-generating it) makes refreshes cheap and deterministic. Surfacing schema-change failures explicitly prevents silent stale results.
**Alternative considered**: Auto re-execute all results on session open — rejected because it is expensive for sessions with many turns and runs queries the user may never scroll to.

### Decision 11: Thinking phase display collapses after first turn
**Choice**: The LLM's thinking block and the generated code block are both expanded by default for the first turn of a session, and collapsed by default for all subsequent turns. Users can expand any turn's thinking or code at any time.
**Rationale**: The thinking phase builds trust on first use. By the second or third turn, repeated expanded reasoning blocks become visual noise. Collapsing them by default preserves the ChatGPT-like conversational feel without hiding the transparency feature.

## Open Questions

- **Embedding model for RAG path**: Use a hosted embedding API (e.g., `text-embedding-3-small`) or a local model (`sentence-transformers`)? Hosted is simpler; local avoids sending knowledge base content to a third party.
- **Knowledge versioning**: Should the system track versions of knowledge files so admins can roll back a bad edit? Git-backed storage vs database-backed versioning.
- **Max execution dataset size**: Proposed 500MB soft limit — reject with a helpful message above that threshold. Confirm.
- **Result pagination**: Proposed 1000 rows max per result, 50 rows per page in the UI. Confirm.
- **Audit log retention**: How long should audit records be kept? Configurable via env var, default 90 days.
