import asyncio
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_routes():
    print("Testing GET / ...")
    r = client.get("/")
    assert r.status_code == 200
    assert "ENDU Runner Scanner" in r.text
    print("GET / OK!")

    print("Testing GET /api/calendar/status ...")
    r = client.get("/api/calendar/status")
    assert r.status_code == 200
    data = r.json()
    assert "is_cached" in data
    print("GET /api/calendar/status OK!", data)

    print("Testing GET /api/search with validation error (empty query) ...")
    r = client.get("/api/search")
    assert r.status_code == 400
    print("Validation 400 OK!")

    print("Testing GET /api/search with Antonio Aiello (1 month) ...")
    r = client.get("/api/search?first_name=Antonio&last_name=Aiello&months=1")
    assert r.status_code == 200
    res = r.json()
    assert res["success"] is True
    print(f"Search OK! Scanned {res['total_events_scanned']} events, found {res['matches_count']} matches in {res['elapsed_seconds']}s")

    print("Testing GET /api/search/stream with SSE ...")
    with client.stream("GET", "/api/search/stream?first_name=Antonio&last_name=Aiello&months=1") as stream_res:
        assert stream_res.status_code == 200
        lines = []
        for line in stream_res.iter_lines():
            if line:
                lines.append(line)
                if "complete" in line or len(lines) >= 10:
                    break
        print(f"Stream OK! Received {len(lines)} SSE lines.")
        assert len(lines) > 0

    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_routes()
