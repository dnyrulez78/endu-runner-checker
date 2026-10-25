import os
import sys

# Assicura che la root del progetto sia in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_routes():
    print("1. Testing GET / ...")
    r = client.get("/")
    assert r.status_code == 200
    assert "ENDU Runner Scanner" in r.text
    print("   GET / OK!")

    print("2. Testing GET /api/calendar/status ...")
    r = client.get("/api/calendar/status")
    assert r.status_code == 200
    assert "is_cached" in r.json()
    print("   GET /api/calendar/status OK!")

    print("3. Testing GET /api/search with validation error ...")
    r = client.get("/api/search")
    assert r.status_code == 400
    print("   Validation 400 OK!")

    print("4. Testing GET /api/search (Future) for Antonio Aiello ...")
    r = client.get("/api/search?first_name=Antonio&last_name=Aiello&months=1")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    print(f"   Future search OK! Found {data['matches_count']} matches in {data['elapsed_seconds']}s")

    print("5. Testing GET /api/results/search (Past Results) for Rossi ...")
    r = client.get("/api/results/search?last_name=Rossi&months=2")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    print(f"   Past results OK! Scanned {data['total_events_scanned']} past events, found {data['matches_count']} in {data['elapsed_seconds']}s")

    print("6. Testing SSE stream for Past Results ...")
    with client.stream("GET", "/api/results/search/stream?last_name=Rossi&months=2") as stream_res:
        assert stream_res.status_code == 200
        count = 0
        for line in stream_res.iter_lines():
            if line:
                count += 1
                if count >= 5:
                    break
        assert count > 0
        print(f"   Past results SSE stream OK! Received {count} packets.")

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_routes()
