# DAItaView

AI-powered data reporting platform. Ask natural language questions about your data and get interactive charts and tables — backed by admin-curated knowledge that teaches the system your company's data context.

## Quickstart

**Requirements**: Docker and Docker Compose.

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Edit .env — at minimum set these:
#    ANTHROPIC_API_KEY=sk-ant-...
#    SECRET_KEY=<random string>
#    SUPERADMIN_EMAIL=admin@yourcompany.com
#    SUPERADMIN_PASSWORD=<strong password>

# 3. Start all services
docker-compose up --build
```

Open http://localhost:3000 and log in with your super-admin credentials.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Your Anthropic API key. |
| `DATABASE_URL` | `postgresql+asyncpg://daitaview:daitaview@db:5432/daitaview` | PostgreSQL connection string. |
| `SECRET_KEY` | `change-me-to-a-long-random-string` | JWT signing secret. Change this. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | JWT session lifetime (minutes). |
| `AUTH_MODE` | `local` | `local`, `oidc`, or `saml`. |
| `SSO_PROVIDER_URL` | — | Required when `AUTH_MODE=oidc` or `saml`. |
| `SSO_CLIENT_ID` | — | SSO client ID. |
| `SSO_CLIENT_SECRET` | — | SSO client secret. |
| `SSO_REDIRECT_URI` | — | SSO callback URL. |
| `SUPERADMIN_EMAIL` | `admin@example.com` | Break-glass super-admin email, seeded on first start. |
| `SUPERADMIN_PASSWORD` | `change-me-immediately` | Super-admin password. Change before first start. |
| `EXECUTION_SERVICE_URL` | `http://execution:8001` | Internal URL for the execution container. |
| `EXECUTION_TIMEOUT_SECONDS` | `30` | Max execution time per query. |
| `EXECUTION_MEMORY_LIMIT_MB` | `512` | Memory cap for the execution container. |
| `MAX_UPLOAD_SIZE_MB` | `500` | Max file size for CSV/JSON/Parquet uploads. |

## First-Run Admin Setup

On first `docker-compose up`, the API seeds a super-admin account using `SUPERADMIN_EMAIL` and `SUPERADMIN_PASSWORD`. This account always works regardless of `AUTH_MODE` — use it as a break-glass account if SSO is misconfigured.

1. Log in at http://localhost:3000/login with your super-admin credentials.
2. Navigate to **Admin → Data Sources** and connect your first data source.
3. Navigate to **Admin → Knowledge** and author knowledge files for that source.
4. Navigate to **Admin → Users** and create user accounts, then assign source permissions.

## Adding a Data Source

**Database (PostgreSQL / MySQL / SQLite)**

1. Go to **Admin → Data Sources → Add Database**.
2. Enter the connection details. The API tests the connection on save and returns a descriptive error if it fails.

**File upload (CSV / JSON / Parquet)**

1. Go to **Admin → Data Sources → Upload file source**.
2. Drag-and-drop or browse to your file. Files are stored in the `uploads/` volume and registered in DuckDB.

After adding a source, click **Refresh Schema** to extract table names, columns, types, and sample rows.

## Authoring Knowledge

Knowledge files live in `knowledge/` and are edited via **Admin → Knowledge** (Monaco editor with live preview).

```
knowledge/
  global.md                          # Layer 1: always included in every prompt
  sources/<source-id>/
    overview.md                      # Layer 2: source-level context
    domains/<domain-name>.md         # Layer 3: domain groupings
    tables/<table-name>.md           # Layer 4: per-table annotations
    examples/<topic>.md              # Few-shot examples
```

**Tips**:
- `global.md` — company-wide business rules, date conventions, currency formats.
- `overview.md` — what this data source represents, how it's updated, who owns it.
- `tables/<name>.md` — column meanings, allowed values, join keys, data quality notes.
- `examples/<topic>.md` — sample questions and the expected output approach.

The **Knowledge Gaps** tab shows questions the system couldn't answer without more context, ranked by frequency. Use these to prioritise what to add to the knowledge base.

## Running E2E Tests

Tests require a running stack (`docker-compose up`).

```bash
cd backend
pip install -e ".[dev]"

# Run all E2E tests
pytest tests/

# Override the API base URL if not running on localhost
TEST_BASE_URL=http://your-server:8000 pytest tests/
```

Tests cover:
- **14.2** `test_e2e_chart_staleness.py` — CSV upload → knowledge → bar chart question → staleness badge
- **14.3** `test_e2e_multiturn.py` — multi-turn follow-up resolution
- **14.4** `test_e2e_table_permission.py` — restricted user blocked from inaccessible table + audit log entry

## Architecture

```
Browser (React + Vite)
    │  HTTP / WebSocket
    ▼
API Service (FastAPI, Python)
    │  SQL                │  HTTP
    ▼                     ▼
PostgreSQL         Execution Service (FastAPI, Docker)
                         │  restricted Python env
                         │  import allowlist, 30s timeout, 512MB RAM
                         ▼
                    DuckDB / SQLAlchemy (data sources)
```

- **API** — auth, sessions, query pipeline, knowledge management, audit logging.
- **Execution** — sandboxed Python runner; no network access, non-root user, allow-listed imports only.
- **PostgreSQL** — all application state: users, sessions, audit log, gap signals.
- **Vector store** — knowledge embeddings for RAG path (pgvector or Chroma, configured at startup).

## Roles

| Role | Capabilities |
|---|---|
| `super_admin` | Full access including user management, audit log, all admin panels. |
| `data_admin` | Connect/delete sources, manage knowledge, assign permissions. Cannot manage other admins. |
| `user` | Ask questions on permitted sources. Cannot access admin panels. |

## SSO Configuration

Set `AUTH_MODE=oidc` and provide `SSO_PROVIDER_URL`, `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_REDIRECT_URI` in `.env`. Restart the API container. The login page will show an SSO button in addition to the local login form.

The local super-admin account remains active regardless of `AUTH_MODE` as a break-glass account.

## Security Notes

- Generated code is scanned for dangerous patterns (`os`, `sys`, `subprocess`, `eval`, etc.) before execution.
- Table references in generated code are validated against the requesting user's permitted set.
- All violations are written to the audit log.
- JWT tokens are stored in memory only (not `localStorage`) and expire after `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Connection credentials are encrypted at rest before being stored in PostgreSQL.
