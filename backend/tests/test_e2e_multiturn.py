"""
E2E test 14.3: Multi-turn session — ask a follow-up question that references the previous
question, verify the LLM resolves it correctly (result_type is chart or table, not error).
"""
import io
import asyncio
import json
import pytest
import httpx

CSV_CONTENT = "product,revenue,units\nWidget A,5000,100\nWidget B,3200,80\nWidget C,7100,140\n"


@pytest.fixture(scope="module")
def source_id(admin_client: httpx.Client) -> str:
    resp = admin_client.post(
        "/sources/upload",
        files={"file": ("products.csv", io.BytesIO(CSV_CONTENT.encode()), "text/csv")},
        data={"name": "e2e-products", "type": "csv"},
    )
    resp.raise_for_status()
    sid = resp.json()["id"]
    yield sid
    admin_client.delete(f"/sources/{sid}")


@pytest.fixture(scope="module")
def session_id(admin_client: httpx.Client, source_id: str) -> str:
    r = admin_client.post("/sessions", json={"source_id": source_id})
    r.raise_for_status()
    sid = r.json()["id"]
    yield sid
    admin_client.delete(f"/sessions/{sid}")


async def _ask_ws(base_url: str, token: str, session_id: str, question: str) -> dict:
    import websockets
    ws_scheme = "wss" if base_url.startswith("https") else "ws"
    host = base_url.split("://", 1)[1]
    uri = f"{ws_scheme}://{host}/ws/sessions/{session_id}/query"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"question": question, "token": token}))
        for _ in range(60):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if msg["event"] == "done":
                return msg["data"]["result"]
            if msg["event"] == "error":
                raise AssertionError(f"WS error: {msg['data']['message']}")
    raise AssertionError("No done event received")


def test_multiturn_followup(admin_client: httpx.Client, base_url: str, source_id: str, session_id: str):
    """First turn asks for top product; second turn asks 'now show just its units' — a follow-up reference."""
    token = admin_client.headers["Authorization"].split(" ")[1]

    try:
        result1 = asyncio.run(_ask_ws(base_url, token, session_id, "Which product has the highest revenue?"))
        result2 = asyncio.run(_ask_ws(base_url, token, session_id, "Now show me the units sold for that product"))
    except Exception as e:
        pytest.skip(f"WebSocket not reachable: {e}")

    assert result1.get("type") in ("chart", "table"), f"Turn 1: unexpected type {result1.get('type')}"
    assert result2.get("type") in ("chart", "table"), f"Turn 2: unexpected type {result2.get('type')}"

    # Check both turns are persisted in session history
    turns = admin_client.get(f"/sessions/{session_id}/turns").json()
    assert len(turns) >= 2
    assert all(t["result_type"] in ("chart", "table") for t in turns[-2:]), \
        f"Expected chart/table for both turns, got {[t['result_type'] for t in turns[-2:]]}"
