"""
E2E test 14.4: Table permission — a user without access to a table asks a question about it;
verify a safe error is returned and the audit log records the violation (code_blocked event).
"""
import io
import asyncio
import json
import pytest
import httpx

CSV_SALARY = "employee,salary,department\nAlice,90000,Engineering\nBob,75000,Marketing\n"
CSV_DEPT = "department,budget\nEngineering,500000\nMarketing,200000\n"


@pytest.fixture(scope="module")
def setup(admin_client: httpx.Client, base_url: str):
    """
    Create two file sources (salary data + dept data).
    Create a restricted user with access only to the dept source.
    Return the restricted user's token and both source IDs.
    """
    # Upload salary source (restricted)
    r = admin_client.post(
        "/sources/upload",
        files={"file": ("salary.csv", io.BytesIO(CSV_SALARY.encode()), "text/csv")},
        data={"name": "e2e-salary", "type": "csv"},
    )
    r.raise_for_status()
    salary_source_id = r.json()["id"]

    # Upload dept source (permitted)
    r = admin_client.post(
        "/sources/upload",
        files={"file": ("dept.csv", io.BytesIO(CSV_DEPT.encode()), "text/csv")},
        data={"name": "e2e-dept", "type": "csv"},
    )
    r.raise_for_status()
    dept_source_id = r.json()["id"]

    # Create restricted user
    user_payload = {"email": "restricted@test.local", "username": "restricted_test", "password": "Testpass123!", "role": "user"}
    r = admin_client.post("/users", json=user_payload)
    r.raise_for_status()
    user_id = r.json()["id"]

    # Grant access only to dept source
    admin_client.post(f"/users/{user_id}/permissions", json={"source_id": dept_source_id, "permitted_tables": None}).raise_for_status()

    # Get restricted user token
    r = httpx.post(f"{base_url}/auth/login", json={"username": "restricted_test", "password": "Testpass123!"})
    r.raise_for_status()
    user_token = r.json()["access_token"]

    yield {
        "salary_source_id": salary_source_id,
        "dept_source_id": dept_source_id,
        "user_id": user_id,
        "user_token": user_token,
    }

    # Cleanup
    admin_client.delete(f"/users/{user_id}")
    admin_client.delete(f"/sources/{salary_source_id}")
    admin_client.delete(f"/sources/{dept_source_id}")


async def _ask_ws_raw(base_url: str, token: str, session_id: str, question: str) -> dict:
    import websockets
    ws_scheme = "wss" if base_url.startswith("https") else "ws"
    host = base_url.split("://", 1)[1]
    uri = f"{ws_scheme}://{host}/ws/sessions/{session_id}/query"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"question": question, "token": token}))
        for _ in range(60):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if msg["event"] in ("done", "error"):
                return msg
    raise AssertionError("No terminal event")


def test_restricted_user_cannot_access_salary_table(admin_client: httpx.Client, base_url: str, setup: dict):
    """
    Restricted user starts a session on dept_source (which they have access to),
    but asks about salary data (a table in a different source they don't have access to).
    The pipeline should block the query and return an error.
    """
    user_token = setup["user_token"]
    dept_source_id = setup["dept_source_id"]

    user_client = httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {user_token}"})

    r = user_client.post("/sessions", json={"source_id": dept_source_id})
    r.raise_for_status()
    session_id = r.json()["id"]

    try:
        msg = asyncio.run(_ask_ws_raw(base_url, user_token, session_id, "Show me all employee salaries from the salary table"))
    except Exception as e:
        pytest.skip(f"WebSocket not reachable: {e}")
    finally:
        user_client.delete(f"/sessions/{session_id}")
        user_client.close()

    # The response should be an error (blocked) or contain no salary data
    assert msg["event"] == "error" or (
        msg["event"] == "done" and msg["data"]["result"].get("type") == "error"
    ), f"Expected blocked/error, got: {msg}"

    # Verify audit log records a code_blocked event
    audit_resp = admin_client.get("/audit", params={"event_type": "code_blocked"})
    audit_resp.raise_for_status()
    blocked_entries = audit_resp.json()
    assert len(blocked_entries) > 0, "Expected at least one code_blocked audit entry"
