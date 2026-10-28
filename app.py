import asyncio
import json
import logging
import os
import time
import webbrowser
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import httpx

from backend.endu_client import EnduClient, DEFAULT_HEADERS as ENDU_DEFAULT_HEADERS
from backend.icron_client import IcronClient, DEFAULT_HEADERS as ICRON_DEFAULT_HEADERS
from backend.fidal_client import FidalClient, FidalSearchResponse
from backend.models import CalendarStatusResponse, PastResultsSearchResponse, SearchResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("endu_tool")

app = FastAPI(
    title="ENDU & ICRON Road Running Checker, Results & FIDAL Archive",
    description="Applicazione locale per verificare le iscrizioni su ENDU e ICRON, consultare lo storico risultati ENDU e l'archivio carriera FIDAL/TDS di Corsa su Strada.",
    version="3.1.0"
)

# Abilita CORS per uso locale
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Istanze dei client singleton con semaforo di concorrenza
endu_client = EnduClient(concurrency_limit=8, cache_ttl_seconds=3600)
icron_client = IcronClient(cache_ttl_seconds=3600, max_concurrency=8)
fidal_client = FidalClient(cache_ttl_seconds=3600)

# Monta le risorse statiche (CSS, JS)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "frontend", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Restituisce l'interfaccia web principale."""
    index_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="File frontend/index.html non trovato.")
    return FileResponse(index_path)


@app.get("/api/calendar/status", response_model=CalendarStatusResponse)
async def get_calendar_status():
    """Restituisce lo stato corrente della cache del calendario gare running di ENDU e ICRON."""
    endu_status = endu_client.get_cache_status()
    icron_status = icron_client.get_cache_status()
    total = endu_status.total_events + icron_status["total_events"]
    is_cached = endu_status.is_cached and icron_status["is_cached"]
    return CalendarStatusResponse(
        is_cached=is_cached,
        total_events=total,
        total_endu_events=endu_status.total_events,
        total_icron_events=icron_status["total_events"],
        date_from=endu_status.date_from,
        date_to=endu_status.date_to,
        cached_at=endu_status.cached_at,
        ttl_seconds_remaining=endu_status.ttl_seconds_remaining
    )


@app.post("/api/calendar/refresh")
async def refresh_calendar(months: int = Query(5, ge=1, le=12)):
    """Invalida la cache locale e riscarica gli eventi di corsa su strada sia da ENDU che da ICRON."""
    try:
        events_e, df_e, dt_e = await endu_client.get_road_running_events(
            months=months,
            force_refresh=True
        )
        events_i, df_i, dt_i = await icron_client.get_running_events(
            months=months,
            force_refresh=True
        )
        total = len(events_e) + len(events_i)
        return {
            "success": True,
            "message": f"Calendario aggiornato con successo: {len(events_e)} gare ENDU + {len(events_i)} gare ICRON ({total} totali).",
            "total_events": total,
            "total_endu": len(events_e),
            "total_icron": len(events_i),
            "date_from": df_e or df_i,
            "date_to": dt_e or dt_i
        }
    except Exception as e:
        logger.error(f"Errore durante l'aggiornamento del calendario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search", response_model=SearchResponse)
async def search_registrations(
    first_name: Optional[str] = Query(None, description="Nome dell'atleta"),
    last_name: Optional[str] = Query(None, description="Cognome dell'atleta"),
    team_code: Optional[str] = Query(None, description="Codice o nome della società sportiva"),
    months: int = Query(5, ge=1, le=12, description="Numero di mesi di orizzonte temporale"),
    exact_date: Optional[str] = Query(None, description="Data specifica (YYYY-MM-DD)"),
    event_name: Optional[str] = Query(None, description="Nome o parola chiave della manifestazione"),
    platform: Optional[str] = Query("all", description="Piattaforma: 'all', 'endu', o 'icron'"),
    force_refresh: bool = Query(False, description="Forza il refresh del calendario eventi")
):
    """
    Endpoint REST sincrono: scansiona gli eventi running nei prossimi N mesi (ENDU e/o ICRON)
    e restituisce l'elenco delle gare a cui l'atleta o la società è iscritta.
    """
    clean_first = first_name.strip() if first_name else ""
    clean_last = last_name.strip() if last_name else ""
    clean_team = team_code.strip() if team_code else ""
    clean_date = exact_date.strip() if exact_date else ""
    clean_event = event_name.strip() if event_name else ""
    clean_platform = (platform or "all").strip().lower()

    if not clean_first and not clean_last and not clean_team:
        raise HTTPException(
            status_code=400,
            detail="Specificare almeno il Cognome, il Nome oppure il Codice Società per effettuare la verifica."
        )

    start_time = time.time()
    try:
        if clean_platform == "endu":
            return await endu_client.scan_events(
                first_name=clean_first or None,
                last_name=clean_last or None,
                team_code=clean_team or None,
                months=months,
                exact_date=clean_date or None,
                event_name=clean_event or None,
                force_refresh=force_refresh
            )
        elif clean_platform == "icron":
            return await icron_client.scan_events(
                first_name=clean_first or None,
                last_name=clean_last or None,
                team_code=clean_team or None,
                months=months,
                exact_date=clean_date or None,
                event_name=clean_event or None,
                force_refresh=force_refresh
            )
        else:
            # Piattaforme combinate (ENDU + ICRON)
            res_endu, res_icron = await asyncio.gather(
                endu_client.scan_events(
                    first_name=clean_first or None,
                    last_name=clean_last or None,
                    team_code=clean_team or None,
                    months=months,
                    exact_date=clean_date or None,
                    event_name=clean_event or None,
                    force_refresh=force_refresh
                ),
                icron_client.scan_events(
                    first_name=clean_first or None,
                    last_name=clean_last or None,
                    team_code=clean_team or None,
                    months=months,
                    exact_date=clean_date or None,
                    event_name=clean_event or None,
                    force_refresh=force_refresh
                ),
                return_exceptions=True
            )

            all_matches = []
            total_scanned = 0
            date_from = ""
            date_to = ""

            if isinstance(res_endu, SearchResponse):
                all_matches.extend(res_endu.results)
                total_scanned += res_endu.total_events_scanned
                date_from = res_endu.date_from
                date_to = res_endu.date_to
            elif isinstance(res_endu, Exception):
                logger.error(f"Errore scansione ENDU: {res_endu}")

            if isinstance(res_icron, SearchResponse):
                all_matches.extend(res_icron.results)
                total_scanned += res_icron.total_events_scanned
                if not date_from:
                    date_from = res_icron.date_from
                if not date_to:
                    date_to = res_icron.date_to
            elif isinstance(res_icron, Exception):
                logger.error(f"Errore scansione ICRON: {res_icron}")

            all_matches.sort(key=lambda m: m.date_from)
            return SearchResponse(
                success=True,
                total_events_scanned=total_scanned,
                matches_count=len(all_matches),
                date_from=date_from,
                date_to=date_to,
                elapsed_seconds=round(time.time() - start_time, 2),
                results=all_matches
            )

    except Exception as e:
        logger.error(f"Errore durante la scansione: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search/stream")
async def search_registrations_stream(
    first_name: Optional[str] = Query(None),
    last_name: Optional[str] = Query(None),
    team_code: Optional[str] = Query(None),
    months: int = Query(5, ge=1, le=12),
    exact_date: Optional[str] = Query(None),
    event_name: Optional[str] = Query(None),
    platform: Optional[str] = Query("all"),
    force_refresh: bool = Query(False)
):
    """
    Endpoint Server-Sent Events (SSE): trasmette in tempo reale il progresso della scansione
    e ogni corrispondenza trovata (da ENDU e/o ICRON) direttamente al browser.
    """
    clean_first = first_name.strip() if first_name else ""
    clean_last = last_name.strip() if last_name else ""
    clean_team = team_code.strip() if team_code else ""
    clean_date = exact_date.strip() if exact_date else ""
    clean_event = event_name.strip() if event_name else ""
    clean_platform = (platform or "all").strip().lower()

    if not clean_first and not clean_last and not clean_team:
        async def err_generator():
            err_payload = {
                "type": "error",
                "message": "Specificare almeno il Cognome, il Nome oppure il Codice Società."
            }
            yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
        return StreamingResponse(err_generator(), media_type="text/event-stream")

    async def sse_event_generator():
        start_time = time.time()
        events_endu = []
        events_icron = []
        date_from = ""
        date_to = ""

        # Recupera manifestazioni ENDU
        if clean_platform in ["all", "endu"]:
            try:
                events_endu, date_from, date_to = await endu_client.get_road_running_events(
                    months=months,
                    exact_date=clean_date or None,
                    event_name=clean_event or None,
                    force_refresh=force_refresh
                )
            except Exception as e:
                logger.error(f"Errore nel recupero calendario ENDU: {e}")

        # Recupera manifestazioni ICRON
        if clean_platform in ["all", "icron"]:
            try:
                events_icron, df_i, dt_i = await icron_client.get_running_events(
                    months=months,
                    exact_date=clean_date or None,
                    event_name=clean_event or None,
                    force_refresh=force_refresh
                )
                if not date_from:
                    date_from = df_i
                if not date_to:
                    date_to = dt_i
            except Exception as e:
                logger.error(f"Errore nel recupero calendario ICRON: {e}")

        total_events = len(events_endu) + len(events_icron)
        init_payload = {
            "type": "init",
            "total": total_events,
            "total_endu": len(events_endu),
            "total_icron": len(events_icron),
            "date_from": date_from,
            "date_to": date_to
        }
        yield f"data: {json.dumps(init_payload, ensure_ascii=False)}\n\n"

        if total_events == 0:
            yield f"data: {json.dumps({'type': 'complete', 'total_scanned': 0, 'total_matches': 0, 'elapsed_seconds': round(time.time() - start_time, 2)}, ensure_ascii=False)}\n\n"
            return

        scanned_counter = 0
        matches_count = 0
        sem_endu = asyncio.Semaphore(8)
        sem_icron = asyncio.Semaphore(8)

        async with httpx.AsyncClient(headers=ENDU_DEFAULT_HEADERS, timeout=12.0) as client_e, \
                   httpx.AsyncClient(headers=ICRON_DEFAULT_HEADERS, timeout=12.0) as client_i:

            async def scan_single_endu(ev):
                m = await endu_client.check_single_event(
                    client_e, sem_endu, ev, clean_first or None, clean_last or None, clean_team or None
                )
                return ("ENDU", ev.get("name") or "Gara ENDU", m)

            async def scan_single_icron(ev):
                m = await icron_client.check_event_entrants(
                    client_i, sem_icron, ev, clean_first or None, clean_last or None, clean_team or None
                )
                return ("ICRON", ev.get("descrizione") or "Gara ICRON", m)

            tasks = [scan_single_endu(ev) for ev in events_endu] + [scan_single_icron(ev) for ev in events_icron]

            for coro in asyncio.as_completed(tasks):
                source, ev_name, match = await coro
                scanned_counter += 1
                if match:
                    matches_count += 1
                    match_payload = {
                        "type": "match",
                        "match": match.model_dump()
                    }
                    yield f"data: {json.dumps(match_payload, ensure_ascii=False)}\n\n"

                progress_payload = {
                    "type": "progress",
                    "scanned": scanned_counter,
                    "total": total_events,
                    "matches": matches_count,
                    "current_event": ev_name,
                    "source": source
                }
                yield f"data: {json.dumps(progress_payload, ensure_ascii=False)}\n\n"

        complete_payload = {
            "type": "complete",
            "total_scanned": total_events,
            "total_matches": matches_count,
            "elapsed_seconds": round(time.time() - start_time, 2)
        }
        yield f"data: {json.dumps(complete_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# =============================================================================
# ENDPOINT PER RISULTATI STORICI E CLASSIFICHE
# =============================================================================

@app.get("/api/results/search", response_model=PastResultsSearchResponse)
async def search_past_results(
    first_name: Optional[str] = Query(None, description="Nome dell'atleta"),
    last_name: Optional[str] = Query(None, description="Cognome dell'atleta"),
    team_code: Optional[str] = Query(None, description="Codice o nome della società sportiva"),
    months: int = Query(12, ge=1, le=24, description="Numero di mesi passati da scansionare"),
    year: Optional[int] = Query(None, ge=2010, le=2030, description="Anno solare specifico (opzionale)"),
    exact_date: Optional[str] = Query(None, description="Data specifica esatta (YYYY-MM-DD)"),
    event_name: Optional[str] = Query(None, description="Nome della manifestazione specifica"),
    force_refresh: bool = Query(False, description="Forza il refresh delle gare passate")
):
    """
    Endpoint REST sincrono: scansiona le manifestazioni passate con classifiche digitali
    e restituisce i piazzamenti, tempi e distacchi dell'atleta o della squadra.
    """
    clean_first = first_name.strip() if first_name else ""
    clean_last = last_name.strip() if last_name else ""
    clean_team = team_code.strip() if team_code else ""
    clean_date = exact_date.strip() if exact_date else ""
    clean_event = event_name.strip() if event_name else ""

    if not clean_first and not clean_last and not clean_team:
        raise HTTPException(
            status_code=400,
            detail="Specificare almeno il Cognome, il Nome oppure la Società per la ricerca storica."
        )

    try:
        return await endu_client.scan_past_results(
            first_name=clean_first or None,
            last_name=clean_last or None,
            team_code=clean_team or None,
            months=months,
            year=year,
            exact_date=clean_date or None,
            event_name=clean_event or None,
            force_refresh=force_refresh
        )
    except Exception as e:
        logger.error(f"Errore durante la scansione dei risultati: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results/search/stream")
async def search_past_results_stream(
    first_name: Optional[str] = Query(None),
    last_name: Optional[str] = Query(None),
    team_code: Optional[str] = Query(None),
    months: int = Query(12, ge=1, le=24),
    year: Optional[int] = Query(None, ge=2010, le=2030),
    exact_date: Optional[str] = Query(None),
    event_name: Optional[str] = Query(None),
    force_refresh: bool = Query(False)
):
    """
    Endpoint Server-Sent Events (SSE) per risultati storici: trasmette live il progresso
    e ogni piazzamento/tempo trovato direttamente al browser.
    """
    clean_first = first_name.strip() if first_name else ""
    clean_last = last_name.strip() if last_name else ""
    clean_team = team_code.strip() if team_code else ""
    clean_date = exact_date.strip() if exact_date else ""
    clean_event = event_name.strip() if event_name else ""

    if not clean_first and not clean_last and not clean_team:
        async def err_generator():
            err_payload = {
                "type": "error",
                "message": "Specificare almeno il Cognome, il Nome o la Società."
            }
            yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
        return StreamingResponse(err_generator(), media_type="text/event-stream")

    async def sse_event_generator():
        async for packet in endu_client.scan_past_results_stream(
            first_name=clean_first or None,
            last_name=clean_last or None,
            team_code=clean_team or None,
            months=months,
            year=year,
            exact_date=clean_date or None,
            event_name=clean_event or None,
            force_refresh=force_refresh
        ):
            yield f"data: {json.dumps(packet, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/fidal/search", response_model=FidalSearchResponse)
async def search_fidal_athlete(
    last_name: str = Query(..., description="Cognome dell'atleta"),
    first_name: Optional[str] = Query(None, description="Nome dell'atleta (opzionale)"),
    year: Optional[int] = Query(None, ge=2000, le=2030, description="Anno specifico (opzionale)"),
    city_or_race: Optional[str] = Query(None, description="Città o nome gara (opzionale)")
):
    """
    Interroga l'archivio federale FIDAL per recuperare la carriera e i risultati ufficiali
    di un atleta (incluse tutte le gare cronometrate da TDS, ENDU, SDAM, WinningTime, ecc.).
    """
    clean_last = last_name.strip()
    clean_first = first_name.strip() if first_name else None
    clean_kw = city_or_race.strip() if city_or_race else None

    if not clean_last:
        raise HTTPException(status_code=400, detail="Inserire il cognome dell'atleta.")

    try:
        return await fidal_client.search_athlete(
            last_name=clean_last,
            first_name=clean_first,
            year=year,
            city_or_race=clean_kw
        )
    except Exception as e:
        logger.error(f"Errore nella ricerca FIDAL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def open_browser_delayed(url: str, delay: float = 1.0):
    """Apre automaticamente il browser predefinito dopo l'avvio del server."""
    async def _opener():
        await asyncio.sleep(delay)
        webbrowser.open(url)
    try:
        asyncio.create_task(_opener())
    except Exception:
        pass


if __name__ == "__main__":
    import threading
    import time
    import uvicorn

    host = "127.0.0.1"
    port = 8000
    local_url = f"http://{host}:{port}"
    
    print("\n" + "=" * 60)
    print("    ENDU ROAD RUNNING CHECKER")
    print("=" * 60)
    print("Server locale avviato con successo!")
    print(f"Apri il tuo browser all'indirizzo: {local_url}")
    print("Premi CTRL+C per arrestare il server.")
    print("=" * 60 + "\n")

    # Apertura automatica del browser
    def _open_browser_thread():
        time.sleep(1.2)
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    threading.Thread(target=_open_browser_thread, daemon=True).start()
    
    uvicorn.run("app:app", host=host, port=port, reload=False, log_level="info")
