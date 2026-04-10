"""Unit tests for the execution engine."""
import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Install restricted importer before importing main
import importer
importer.install()

from main import app

client = TestClient(app)


def test_success_table():
    code = "import pandas as pd\nresult = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})"
    resp = client.post("/execute", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "table"
    assert data["data"]["columns"] == ["a", "b"]
    assert len(data["data"]["rows"]) == 2


def test_success_chart():
    code = (
        "import pandas as pd\nimport plotly.express as px\n"
        "df = pd.DataFrame({'x': [1,2,3], 'y': [4,5,6]})\n"
        "result = px.line(df, x='x', y='y')"
    )
    resp = client.post("/execute", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "chart"


def test_blocked_import():
    code = "import os\nresult = os.listdir('.')"
    resp = client.post("/execute", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "error"
    assert data["error_type"] == "import"


def test_no_output():
    code = "x = 1 + 1"
    resp = client.post("/execute", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "empty"


def test_runtime_error():
    code = "result = 1 / 0"
    resp = client.post("/execute", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "error"
    assert data["error_type"] == "runtime"


def test_schema_change_error():
    code = "import pandas as pd\nimport duckdb\nresult = duckdb.sql('SELECT nonexistent_column FROM nonexistent_table').df()"
    resp = client.post("/execute", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "error"
    assert data["error_type"] == "schema_change"
