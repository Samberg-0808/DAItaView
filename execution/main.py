"""
Execution service — runs generated Python code in a restricted environment.
Accepts POST /execute, returns structured result.
"""
import json
import os
import resource
import signal
import textwrap
import traceback
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

import importer  # install restricted importer on startup
importer.install()

TIMEOUT = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", "30"))
MEMORY_LIMIT_MB = int(os.getenv("EXECUTION_MEMORY_LIMIT_MB", "512"))

app = FastAPI(title="DAItaView Execution Service")


class ExecuteRequest(BaseModel):
    code: str
    data_source_config: dict | None = None  # passed as context variable `_ds_config`


class ExecuteResponse(BaseModel):
    type: str          # "chart" | "table" | "empty" | "error"
    data: Any = None   # Plotly JSON dict | {columns, rows} | None
    error: str | None = None
    error_type: str | None = None  # "schema_change" | "timeout" | "memory" | "import" | "runtime"
    warnings: list[str] = []


def _set_memory_limit():
    limit_bytes = MEMORY_LIMIT_MB * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
    except Exception:
        pass  # not all platforms support RLIMIT_AS


def _timeout_handler(signum, frame):
    raise TimeoutError(f"Execution exceeded {TIMEOUT}s limit")


def _serialize_result(result: Any) -> ExecuteResponse:
    import pandas as pd

    try:
        import plotly.graph_objects as go
        if isinstance(result, go.Figure):
            return ExecuteResponse(type="chart", data=result.to_json())
    except Exception:
        pass

    if isinstance(result, pd.DataFrame):
        rows = result.head(1000).to_dict(orient="records")
        columns = list(result.columns)
        return ExecuteResponse(type="table", data={"columns": columns, "rows": rows})

    return ExecuteResponse(type="empty", warnings=["Code ran successfully but produced no output."])


@app.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest) -> ExecuteResponse:
    _set_memory_limit()
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(TIMEOUT)

    namespace: dict[str, Any] = {}
    if req.data_source_config:
        namespace["_ds_config"] = req.data_source_config

    try:
        exec(compile(req.code, "<generated>", "exec"), namespace)  # noqa: S102
        signal.alarm(0)
    except TimeoutError as e:
        signal.alarm(0)
        return ExecuteResponse(type="error", error=str(e), error_type="timeout")
    except MemoryError:
        signal.alarm(0)
        return ExecuteResponse(type="error", error="Memory limit exceeded", error_type="memory")
    except ImportError as e:
        signal.alarm(0)
        return ExecuteResponse(type="error", error=str(e), error_type="import")
    except Exception as e:
        signal.alarm(0)
        err_msg = str(e)
        # Detect schema-change errors
        error_type = "runtime"
        lower = err_msg.lower()
        if any(kw in lower for kw in ["column", "table", "does not exist", "no such", "not found"]):
            error_type = "schema_change"
        return ExecuteResponse(type="error", error=err_msg, error_type=error_type)

    result = namespace.get("result")
    if result is None:
        return ExecuteResponse(type="empty", warnings=["Code ran successfully but produced no output."])

    return _serialize_result(result)


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
