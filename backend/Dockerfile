FROM python:3.11-slim

WORKDIR /app

# Install application dependencies
RUN pip install --no-cache-dir \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.29.0" \
    "anthropic>=0.28.0" \
    "pandas>=2.2.0" \
    "duckdb>=0.10.0" \
    "plotly>=5.22.0" \
    "sqlalchemy>=2.0.0" \
    "alembic>=1.13.0" \
    "asyncpg>=0.29.0" \
    "psycopg2-binary>=2.9.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "bcrypt<4.0.0" \
    "authlib>=1.3.0" \
    "httpx>=0.27.0" \
    "sentence-transformers>=3.0.0" \
    "tiktoken>=0.7.0" \
    "python-multipart>=0.0.9" \
    "pydantic>=2.7.0" \
    "pydantic-settings>=2.3.0" \
    "cryptography>=42.0.0" \
    "pyarrow>=16.0.0" \
    "python-dotenv>=1.0.0"

# Copy source into backend/ so `from backend.x import ...` works
COPY . backend/

# /app must be on PYTHONPATH so `from backend.x import` resolves from /app/backend/
ENV PYTHONPATH=/app

CMD ["sh", "-c", "cd /app/backend && alembic upgrade head && cd /app && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
