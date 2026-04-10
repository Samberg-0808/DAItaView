FROM python:3.11-slim

# Non-root user for security
RUN groupadd -r executor && useradd -r -g executor executor

WORKDIR /app

# Install only allowlisted packages + FastAPI for the service endpoint
RUN pip install --no-cache-dir \
    fastapi==0.111.0 \
    uvicorn==0.29.0 \
    pandas==2.2.2 \
    numpy==1.26.4 \
    duckdb==0.10.3 \
    plotly==5.22.0 \
    pyarrow==16.0.0 \
    && rm -rf /root/.cache

COPY main.py .
COPY importer.py .

RUN chown -R executor:executor /app

USER executor

# No network access enforced at docker-compose level (internal network only)
EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
