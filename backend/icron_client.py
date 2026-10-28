"""
Client asincrono per l'interrogazione delle manifestazioni e degli iscritti sulla piattaforma ICRON (icron.it).
Fornisce scansione del calendario gare running e verifica delle iscrizioni future di atleti e società sportive.
"""

import asyncio
from datetime import date, datetime, timedelta
import logging
import re
import time
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import httpx

from backend.models import CalendarStatusResponse, EntrantResult, EventMatch, SearchResponse

logger = logging.getLogger("endu_tool.icron")

ICRON_BASE_URL = "https://www.icron.it"
ICRON_OPEN_EVENTS_URL = f"{ICRON_BASE_URL}/IcronNewGO/getOpenEvents"
ICRON_ISCRIZIONI_URL = f"{ICRON_BASE_URL}/IcronNewGO/getIscrizioni"
ICRON_CLASSIFICA_URL = f"{ICRON_BASE_URL}/IcronNewGO/getClassifica"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": ICRON_BASE_URL,
    "Referer": f"{ICRON_BASE_URL}/newgo/"
}

MONTH_NAMES_IT = {
    1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "Mag", 6: "Giu", 7: "Lug", 8: "Ago",
    9: "Set", 10: "Ott", 11: "Nov", 12: "Dic"
}


def parse_icron_date(date_str: Optional[str]) -> Optional[date]:
    """Interpreta stringhe di data ICRON in formato DD-MM-YYYY o YYYY-MM-DD."""
    if not date_str:
        return None
    clean = date_str.strip()
    # DD-MM-YYYY (es. 24-01-2027)
    m1 = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})", clean)
    if m1:
        try:
            return date(int(m1.group(3)), int(m1.group(2)), int(m1.group(1)))
        except ValueError:
            return None
    # YYYY-MM-DD (es. 2027-01-24 00:00:00.0)
    m2 = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", clean)
    if m2:
        try:
            return date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
        except ValueError:
            return None
    return None


def format_icron_date(d: date) -> str:
    """Formatta un oggetto date in GG Mmm AAAA (es. 24 Gen 2027)."""
    month_name = MONTH_NAMES_IT.get(d.month, str(d.month))
    return f"{d.day:02d} {month_name} {d.year}"


class IcronClient:
    """Client per la consultazione del calendario gare e iscritti su ICRON."""

    def __init__(self, cache_ttl_seconds: int = 3600, max_concurrency: int = 8):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_concurrency = max_concurrency
        self._events_cache: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_lock = asyncio.Lock()

    def is_cache_valid(self) -> bool:
        if self._events_cache is None or self._cache_timestamp is None:
            return False
        return (time.time() - self._cache_timestamp) < self.cache_ttl_seconds

    def get_cache_status(self) -> Dict:
        valid = self.is_cache_valid()
        ttl_left = None
        if valid and self._cache_timestamp:
            ttl_left = max(0, int(self.cache_ttl_seconds - (time.time() - self._cache_timestamp)))
        return {
            "is_cached": valid,
            "total_events": len(self._events_cache) if self._events_cache else 0,
            "ttl_seconds_remaining": ttl_left
        }

    async def get_running_events(
        self,
        months: int = 5,
        exact_date: Optional[str] = None,
        event_name: Optional[str] = None,
        force_refresh: bool = False
    ) -> Tuple[List[Dict], str, str]:
        """
        Recupera e memorizza in cache tutte le manifestazioni di corsa su strada di ICRON
        filtrate per l'orizzonte temporale specificato (e per data o nome gara se forniti).
        """
        async with self._cache_lock:
            if force_refresh or not self.is_cache_valid():
                logger.info("Aggiornamento del calendario manifestazioni da ICRON...")
                async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0) as client:
                    payload = {"nrEventi": 1000, "pageSize": "200", "pageIndex": 0, "flagComplete": True}
                    resp = await client.post(ICRON_OPEN_EVENTS_URL, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    raw_events = data.get("listaEventi", [])

                # Filtra eventi di corsa (running / trail)
                running_events = []
                for ev in raw_events:
                    sport = str(ev.get("sport") or "").upper()
                    desc = str(ev.get("descrizione") or "").lower()
                    if sport in ["RUNNING", "RUNNING TRAIL"] or any(k in desc for k in ["maraton", "corsa", "10km", "mezza", "podist"]):
                        running_events.append(ev)

                self._events_cache = running_events
                self._cache_timestamp = time.time()
                logger.info(f"Calendario ICRON aggiornato: {len(running_events)} gare running in cache.")

        all_events = self._events_cache or []
        today = date.today()
        end_date = today + timedelta(days=int(months * 30.5))

        exact_filter_date: Optional[date] = None
        if exact_date:
            try:
                exact_filter_date = date.fromisoformat(exact_date.strip())
            except ValueError:
                exact_filter_date = parse_icron_date(exact_date.strip())

        filtered: List[Dict] = []
        for ev in all_events:
            ev_date = parse_icron_date(ev.get("dataEvento"))
            if not ev_date:
                continue

            # Filtro temporale standard
            if not (today <= ev_date <= end_date):
                # Se è stato impostato un exact_date al di fuori dell'orizzonte standard, lo consideriamo
                if not (exact_filter_date and ev_date == exact_filter_date):
                    continue

            # Filtro data esatta
            if exact_filter_date and ev_date != exact_filter_date:
                continue

            # Filtro nome manifestazione o città
            if event_name:
                kw = event_name.strip().lower()
                desc = str(ev.get("descrizione") or "").lower()
                loc = str(ev.get("localita") or "").lower()
                reg = str(ev.get("regione") or "").lower()
                if kw not in desc and kw not in loc and kw not in reg:
                    continue

            # Arricchisci l'oggetto evento con data parsed
            ev_copy = dict(ev)
            ev_copy["_parsed_date"] = ev_date
            filtered.append(ev_copy)

        # Ordina cronologicamente
        filtered.sort(key=lambda x: x["_parsed_date"])

        date_from_str = today.isoformat()
        date_to_str = end_date.isoformat()
        return filtered, date_from_str, date_to_str

    async def check_event_entrants(
        self,
        client: httpx.AsyncClient,
        sem: asyncio.Semaphore,
        event: Dict,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        team_code: Optional[str] = None
    ) -> Optional[EventMatch]:
        """Verifica se l'atleta o la società è presente nella lista iscritti della gara ICRON."""
        event_id = str(event.get("idGara"))
        clean_first = first_name.strip().lower() if first_name else ""
        clean_last = last_name.strip().lower() if last_name else ""
        clean_team = team_code.strip().lower() if team_code else ""

        # Prepara payload per ICRON getIscrizioni.
        # ICRON richiede il parametro "criterio" ("squadra:..." o "cognome:...")
        # per effettuare la ricerca tramite la funzione "Verifica Iscrizione",
        # permettendo di trovare gli atleti anche quando la lista completa non è resa pubblica.
        payload: Dict[str, str] = {"idGara": event_id}
        has_team_criterio = False
        if clean_team:
            payload["criterio"] = f"squadra:{clean_team}"
            has_team_criterio = True
        elif clean_last:
            payload["criterio"] = f"cognome:{clean_last}"
        elif clean_first:
            payload["criterio"] = f"cognome:{clean_first}"

        async with sem:
            try:
                resp = await client.post(
                    ICRON_ISCRIZIONI_URL,
                    json=payload,
                    timeout=12.0
                )
                if resp.status_code != 200:
                    return None
                
                res_json = resp.json()
                raw_participants = res_json.get("elencoPartecipanti", [])
                if not raw_participants:
                    return None

                matched_entrants: List[EntrantResult] = []
                for p in raw_participants:
                    p_last = str(p.get("cognome") or "").strip().lower()
                    p_first = str(p.get("nome") or "").strip().lower()
                    p_team = str(p.get("squadra") or "").strip().lower()
                    p_tessera = str(p.get("tessera") or "").strip().lower()
                    p_ente = str(p.get("ente") or "").strip().lower()

                    # Verifica Cognome
                    if clean_last and clean_last not in p_last:
                        continue

                    # Verifica Nome
                    if clean_first and clean_first not in p_first:
                        continue

                    # Verifica Società / Codice (se non già filtrato dal server tramite criterio=squadra:...)
                    if clean_team and not has_team_criterio:
                        team_match = (
                            clean_team in p_team or
                            clean_team in p_tessera or
                            clean_team in p_ente
                        )
                        if not team_match:
                            continue

                    # Estrai anno di nascita
                    birth_year = None
                    birth_str = p.get("dataNascita")
                    if birth_str:
                        m = re.search(r"\b(19\d{2}|20\d{2})\b", str(birth_str))
                        if m:
                            birth_year = int(m.group(1))

                    # Pettorale
                    bib = p.get("pettorale") or p.get("pettoraleMaster")
                    bib_str = str(bib).strip() if bib and str(bib).strip() not in ["0", "None"] else None

                    item_first = str(p.get("nome") or "").strip().title()
                    item_last = str(p.get("cognome") or "").strip().upper()
                    full_name = f"{item_first} {item_last}".strip()

                    entrant = EntrantResult(
                        first_name=item_first,
                        last_name=item_last,
                        full_name=full_name,
                        bib=bib_str,
                        year_of_birth=birth_year,
                        nationality=p.get("nazione"),
                        category=p.get("categoria"),
                        team_name=p.get("squadra") or None,
                        team_code=p.get("tessera") or None,
                        course_name=p.get("divisione") or None
                    )
                    matched_entrants.append(entrant)

                if not matched_entrants:
                    return None

                ev_date: date = event.get("_parsed_date") or parse_icron_date(event.get("dataEvento")) or date.today()
                date_from_iso = ev_date.isoformat()
                date_formatted = format_icron_date(ev_date)

                city = event.get("localita")
                region = event.get("regione")
                if city and region:
                    location_formatted = f"{city} ({region})"
                elif city:
                    location_formatted = city
                elif region:
                    location_formatted = region
                else:
                    location_formatted = "Italia"

                event_url = f"{ICRON_BASE_URL}/newgo/#/evento/{event_id}"

                return EventMatch(
                    event_id=event_id,
                    name=event.get("descrizione") or "Gara ICRON",
                    slug=f"icron-{event_id}",
                    event_url=event_url,
                    verify_url=event_url,
                    date_from=date_from_iso,
                    date_formatted=date_formatted,
                    city=city,
                    district=region,
                    location_formatted=location_formatted,
                    source="ICRON",
                    entrants=matched_entrants
                )

            except Exception as e:
                logger.debug(f"Errore controllo iscritti ICRON evento {event_id}: {e}")
                return None

    async def scan_events(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        team_code: Optional[str] = None,
        months: int = 5,
        exact_date: Optional[str] = None,
        event_name: Optional[str] = None,
        force_refresh: bool = False
    ) -> SearchResponse:
        """Esegue la scansione completa di tutti gli eventi ICRON pertinenti."""
        start_time = time.time()
        events, date_from, date_to = await self.get_running_events(
            months=months,
            exact_date=exact_date,
            event_name=event_name,
            force_refresh=force_refresh
        )

        sem = asyncio.Semaphore(self.max_concurrency)
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=12.0) as client:
            tasks = [
                self.check_event_entrants(client, sem, ev, first_name, last_name, team_code)
                for ev in events
            ]
            results_or_none = await asyncio.gather(*tasks)

        matches = [m for m in results_or_none if m is not None]
        matches.sort(key=lambda m: m.date_from)

        return SearchResponse(
            success=True,
            total_events_scanned=len(events),
            matches_count=len(matches),
            date_from=date_from,
            date_to=date_to,
            elapsed_seconds=round(time.time() - start_time, 2),
            results=matches
        )
