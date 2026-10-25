import asyncio
import json
import logging
import os
import webbrowser
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.endu_client import EnduClient
from backend.fidal_client import FidalClient, FidalSearchResponse
from backend.models import CalendarStatusResponse, PastResultsSearchResponse, SearchResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("endu_tool")

app = FastAPI(
    title="ENDU Road Running Registration Checker & Results",
    description="Applicazione locale per verificare le iscrizioni, consultare lo storico risultati ENDU e l'archivio carriera FIDAL/TDS di Corsa su Strada.",
    version="3.0.0"
)

# Abilita CORS per uso locale
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Istanza del client ENDU singleton con semaforo a 8 connessioni contemporanee
endu_client = EnduClient(concurrency_limit=8, cache_ttl_seconds=3600)
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
    """Restituisce lo stato corrente della cache del calendario gare running."""
    return endu_client.get_cache_status()


@app.post("/api/calendar/refresh")
async def refresh_calendar(months: int = Query(5, ge=1, le=12)):
    """Invalida la cache locale e riscarica gli eventi di corsa su strada da ENDU."""
    try:
        events, date_from, date_to = await endu_client.get_road_running_events(
            months=months,
            force_refresh=True
        )
        return {
            "success": True,
            "message": f"Calendario aggiornato con successo: {len(events)} manifestazioni running caricate.",
            "total_events": len(events),
            "date_from": date_from,
            "date_to": date_to
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
    force_refresh: bool = Query(False, description="Forza il refresh del calendario eventi")
):
    """
    Endpoint REST sincrono: scansiona tutti gli eventi running nei prossimi N mesi
    e restituisce l'elenco delle gare a cui l'atleta o la società è iscritta.
    """
    clean_first = first_name.strip() if first_name else ""
    clean_last = last_name.strip() if last_name else ""
    clean_team = team_code.strip() if team_code else ""
    clean_date = exact_date.strip() if exact_date else ""
    clean_event = event_name.strip() if event_name else ""

    if not clean_first and not clean_last and not clean_team:
        raise HTTPException(
            status_code=400,
            detail="Specificare almeno il Cognome, il Nome oppure il Codice Società per effettuare la verifica."
        )

    try:
        return await endu_client.scan_events(
            first_name=clean_first or None,
            last_name=clean_last or None,
            team_code=clean_team or None,
            months=months,
            exact_date=clean_date or None,
            event_name=clean_event or None,
            force_refresh=force_refresh
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
    force_refresh: bool = Query(False)
):
    """
    Endpoint Server-Sent Events (SSE): trasmette in tempo reale il progresso della scansione
    e ogni corrispondenza trovata direttamente al browser.
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
                "message": "Specificare almeno il Cognome, il Nome oppure il Codice Società."
            }
            yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
        return StreamingResponse(err_generator(), media_type="text/event-stream")

    async def sse_event_generator():
        async for packet in endu_client.scan_events_stream(
            first_name=clean_first or None,
            last_name=clean_last or None,
            team_code=clean_team or None,
            months=months,
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
