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

    print("7. Testing exact date search (2024-05-25) ...")
    r = client.get("/api/results/search?last_name=Rossi&exact_date=2024-05-25")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    print(f"   Exact date search OK! Scanned {data['total_events_scanned']} events in {data['elapsed_seconds']}s, found {data['matches_count']} matches.")

    print("8. Testing event name search (event_name=Moonlight) ...")
    r = client.get("/api/results/search?last_name=Rossi&event_name=Moonlight&year=2024")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    print(f"   Event name search OK! Scanned {data['total_events_scanned']} events in {data['elapsed_seconds']}s, found {data['matches_count']} matches.")

    print("9. Testing SSE stream with event_name='jesolo' and year=2024 ...")
    with client.stream("GET", "/api/results/search/stream?last_name=marchesan&event_name=jesolo&year=2024") as stream_res:
        assert stream_res.status_code == 200
        packets = []
        for line in stream_res.iter_lines():
            if line and line.startswith("data: "):
                import json
                p = json.loads(line[6:])
                packets.append(p)
        assert len(packets) >= 2
        # Verifica che il total scansionato sia le sole gare di Jesolo (2 gare: RunDaddy e Moonlight Half Marathon)
        init_pkt = packets[0]
        assert init_pkt["type"] == "init"
        assert init_pkt["total"] in [1, 2]
        print(f"   Jesolo SSE stream OK! Scanned exactly {init_pkt['total']} events in Jesolo and found {len(packets)-2} match packets!")

    print("10. Testing historical year back to 2015 ...")
    r = client.get("/api/results/search?last_name=Rossi&year=2015&event_name=Milano")
    assert r.status_code == 200
    assert r.json()["success"] is True
    print("   Year 2015 search OK!")

    print("11. Testing FIDAL athlete archive for Danny Marchesan ...")
    r = client.get("/api/fidal/search?last_name=marchesan&first_name=danny")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["athlete"] is not None
    assert "VICENZA RUNNERS" in data["athlete"]["society"]
    assert data["athlete"]["total_results"] >= 20

    # Test year 2019 filter on FIDAL
    r_2019 = client.get("/api/fidal/search?last_name=marchesan&first_name=danny&year=2019&city_or_race=vicenza")
    assert r_2019.status_code == 200
    d_2019 = r_2019.json()
    assert d_2019["athlete"]["total_results"] == 1
    race_vic = d_2019["athlete"]["results"][0]
    assert race_vic["city"] == "Vicenza"
    assert "1h44:39" in race_vic["time"]
    print(f"   FIDAL search OK! Verified Vicenza 2019: {race_vic['full_date']} {race_vic['time']} ({race_vic['rank_cleaned']})")

    print("12. Testing ICRON search for Carlo Croci ...")
    r_icron = client.get("/api/search?first_name=Carlo&last_name=Croci&platform=icron&months=12")
    assert r_icron.status_code == 200
    d_icron = r_icron.json()
    assert d_icron["success"] is True
    assert d_icron["matches_count"] >= 1
    assert d_icron["results"][0]["source"] == "ICRON"
    assert "FOLIGNO" in d_icron["results"][0]["name"].upper()
    print(f"   ICRON search OK! Found {d_icron['matches_count']} matches (Sample: {d_icron['results'][0]['name']} - {d_icron['results'][0]['entrants'][0]['full_name']})")

    print("13. Testing combined SSE stream (ENDU + ICRON) ...")
    with client.stream("GET", "/api/search/stream?first_name=Carlo&last_name=Croci&platform=all&months=12&event_name=Foligno") as s_res:
        assert s_res.status_code == 200
        packets = []
        for line in s_res.iter_lines():
            if line and line.startswith("data: "):
                import json
                p = json.loads(line[6:])
                packets.append(p)
        assert len(packets) >= 2
        init_pkt = packets[0]
        assert init_pkt["type"] == "init"
        match_pkts = [p for p in packets if p.get("type") == "match"]
        assert len(match_pkts) >= 1
        assert match_pkts[0]["match"]["source"] == "ICRON"
        print(f"   Combined SSE stream OK! Verified ICRON match in live stream.")

    print("14. Testing ICRON search for team_code=vi654 (Vicenza Runners) ...")
    r_team = client.get("/api/search?team_code=vi654&platform=icron&months=5")
    assert r_team.status_code == 200
    d_team = r_team.json()
    assert d_team["success"] is True
    assert d_team["matches_count"] >= 1
    # Check that iRun21 is found with Danny Marchesan
    irun = next((m for m in d_team["results"] if "irun" in m["name"].lower() or "vicenza" in m["name"].lower()), None)
    assert irun is not None
    assert any("MARCHESAN" in ent["full_name"].upper() for ent in irun["entrants"])
    print(f"   ICRON team search OK! Found {d_team['matches_count']} races for vi654 including {irun['name']}.")

    print("15. Testing Wedosport Trail career search for Danny Marchesan ...")
    r_wedo = client.get("/api/wedosport/search?last_name=marchesan&first_name=danny")
    assert r_wedo.status_code == 200
    d_wedo = r_wedo.json()
    assert d_wedo["success"] is True
    assert d_wedo["athlete"] is not None
    assert "MARCHESAN" in d_wedo["athlete"]["name"].upper()
    assert len(d_wedo["athlete"]["results"]) >= 3
    ultra = next((r for r in d_wedo["athlete"]["results"] if "ultrabericus" in r["race_name"].lower()), None)
    assert ultra is not None
    assert "65" in ultra["distance_km"] or "65" in ultra["distance_name"]
    print(f"   Wedosport career OK! Verified {d_wedo['athlete']['name']}: {ultra['race_name']} {ultra['distance_km']} - Tempo: {ultra['time']} (Pos: {ultra['rank_cleaned']})")

    print("16. Testing Wedosport future entrant search for last_name=bianquin ...")
    r_wf = client.get("/api/search?last_name=bianquin&platform=wedosport&months=5")
    assert r_wf.status_code == 200
    d_wf = r_wf.json()
    assert d_wf["success"] is True
    assert d_wf["matches_count"] >= 1
    assert d_wf["results"][0]["source"] == "WEDOSPORT"
    print(f"   Wedosport future search OK! Found {d_wf['matches_count']} matches (Sample: {d_wf['results'][0]['name']})")

    print("17. Testing combined SSE stream (ENDU + ICRON + Wedosport) ...")
    with client.stream("GET", "/api/search/stream?first_name=Stefano&last_name=Baronio&platform=all&months=5") as s_res3:
        assert s_res3.status_code == 200
        packets = []
        for line in s_res3.iter_lines():
            if line and line.startswith("data: "):
                import json
                p = json.loads(line[6:])
                packets.append(p)
        assert len(packets) >= 2
        init_pkt = packets[0]
        assert init_pkt["type"] == "init"
        assert init_pkt["total_wedosport"] >= 1
        match_pkts = [p for p in packets if p.get("type") == "match"]
        assert len(match_pkts) >= 1
        assert any(p["match"]["source"] == "WEDOSPORT" for p in match_pkts)
        print(f"   Combined 3-platform SSE stream OK! Verified Wedosport match in live stream.")

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_routes()
