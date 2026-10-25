import asyncio
import calendar
import datetime
import time
from typing import AsyncGenerator, Dict, List, Optional, Tuple
import httpx

from backend.models import (
    CalendarStatusResponse,
    EntrantResult,
    EventMatch,
    PastEventResultMatch,
    PastResultsSearchResponse,
    RaceResultItem,
    SearchResponse,
)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "x-endu-client": "endu-web",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.endu.net/it/events",
    "Origin": "https://www.endu.net",
}

BASE_API_URL = "https://www.endu.net/api"

ITALIAN_MONTHS = [
    "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
    "Lug", "Ago", "Set", "Ott", "Nov", "Dic"
]


def add_months(source_date: datetime.date, months: int) -> datetime.date:
    """Calcola una data futura o passata aggiungendo/sottraendo un numero specificato di mesi."""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def format_iso_date(iso_str: str) -> str:
    """Formatta una data ISO in formato leggibile GG Mmm AAAA (es. 15 Nov 2026)."""
    if not iso_str:
        return ""
    try:
        clean_str = iso_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(clean_str)
        month_name = ITALIAN_MONTHS[dt.month - 1]
        return f"{dt.day:02d} {month_name} {dt.year}"
    except Exception:
        if len(iso_str) >= 10:
            parts = iso_str[:10].split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return iso_str


class EnduClient:
    """
    Client asincrono ad alte prestazioni per interagire con le API di ENDU.
    Gestisce:
      1. La verifica delle iscrizioni future alle gare di Corsa su Strada.
      2. La consultazione dello storico risultati e classifiche delle gare passate.
    """

    def __init__(self, concurrency_limit: int = 8, cache_ttl_seconds: int = 3600):
        self.concurrency_limit = concurrency_limit
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # Cache calendario gare future
        self._cached_events: Optional[List[Dict]] = None
        self._cache_timestamp: float = 0.0
        self._cache_date_from: Optional[str] = None
        self._cache_date_to: Optional[str] = None

        # Cache calendario gare passate con risultati
        self._cached_past_events: Optional[List[Dict]] = None
        self._past_cache_timestamp: float = 0.0
        self._past_cache_date_from: Optional[str] = None
        self._past_cache_date_to: Optional[str] = None

        self._cache_lock: Optional[asyncio.Lock] = None
        self._cache_lock_loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_cache_lock(self) -> asyncio.Lock:
        """Garantisce un Lock associato all'event loop correntemente in esecuzione."""
        loop = asyncio.get_running_loop()
        if self._cache_lock is None or self._cache_lock_loop != loop:
            self._cache_lock = asyncio.Lock()
            self._cache_lock_loop = loop
        return self._cache_lock

    def get_cache_status(self) -> CalendarStatusResponse:
        """Restituisce lo stato attuale della cache del calendario gare future."""
        now = time.time()
        elapsed = now - self._cache_timestamp
        is_valid = bool(self._cached_events is not None and elapsed < self.cache_ttl_seconds)
        
        ttl_remaining = max(0, int(self.cache_ttl_seconds - elapsed)) if is_valid else 0
        cached_at_str = (
            datetime.datetime.fromtimestamp(self._cache_timestamp).strftime("%d/%m/%Y %H:%M:%S")
            if self._cache_timestamp > 0 else None
        )
        
        return CalendarStatusResponse(
            is_cached=is_valid,
            total_events=len(self._cached_events) if self._cached_events else 0,
            date_from=self._cache_date_from,
            date_to=self._cache_date_to,
            cached_at=cached_at_str,
            ttl_seconds_remaining=ttl_remaining if is_valid else None
        )

    def invalidate_cache(self):
        """Invalida forzatamente la cache in memoria."""
        self._cached_events = None
        self._cache_timestamp = 0.0
        self._cache_date_from = None
        self._cache_date_to = None
        self._cached_past_events = None
        self._past_cache_timestamp = 0.0
        self._past_cache_date_from = None
        self._past_cache_date_to = None

    # =========================================================================
    # 1. FUNZIONALITÀ GARE FUTURE (ISCRIZIONI)
    # =========================================================================

    async def get_road_running_events(
        self,
        months: int = 5,
        force_refresh: bool = False
    ) -> Tuple[List[Dict], str, str]:
        """
        Recupera tutte le manifestazioni future di Corsa su Strada da ENDU.
        """
        today = datetime.date.today()
        end_date = add_months(today, months)
        date_from_str = today.strftime("%Y-%m-%d")
        date_to_str = end_date.strftime("%Y-%m-%d")

        now = time.time()
        lock = self._get_cache_lock()
        async with lock:
            if not force_refresh and self._cached_events is not None:
                if (now - self._cache_timestamp) < self.cache_ttl_seconds:
                    if self._cache_date_from == date_from_str and self._cache_date_to == date_to_str:
                        return self._cached_events, date_from_str, date_to_str

        collected_events: List[Dict] = []
        sequence_token: Optional[str] = None
        page_size = 500

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0) as client:
            while True:
                params = {
                    "dateFrom": date_from_str,
                    "dateTo": date_to_str,
                    "discipline": "road_running",
                    "pageSize": page_size,
                    "sort": "date.from"
                }
                if sequence_token:
                    params["sequenceToken"] = sequence_token

                response = await client.get(f"{BASE_API_URL}/events", params=params)
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                
                for item in items:
                    discipline_id = item.get("discipline", {}).get("id")
                    sport_id = item.get("sport", {}).get("id")
                    if discipline_id == "road_running" or (sport_id == "running" and discipline_id != "trail_running"):
                        collected_events.append(item)

                total_items = data.get("totalItems", len(items))
                if len(items) < page_size or len(collected_events) >= total_items or not items:
                    break
                
                last_token = items[-1].get("sequenceToken")
                if not last_token or last_token == sequence_token:
                    break
                sequence_token = last_token

        async with lock:
            self._cached_events = collected_events
            self._cache_timestamp = time.time()
            self._cache_date_from = date_from_str
            self._cache_date_to = date_to_str

        return collected_events, date_from_str, date_to_str

    async def check_single_event(
        self,
        client: httpx.AsyncClient,
        sem: asyncio.Semaphore,
        event: Dict,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        team_code: Optional[str] = None
    ) -> Optional[EventMatch]:
        """
        Verifica se l'atleta o la società è iscritta a un evento futuro.
        """
        event_id = event.get("id")
        if not event_id:
            return None

        clean_first = first_name.strip() if first_name else None
        clean_last = last_name.strip() if last_name else None
        clean_team = team_code.strip() if team_code else None

        params: Dict[str, str] = {}
        if clean_first or clean_last:
            if clean_first and len(clean_first) >= 2:
                params["firstName"] = clean_first
            if clean_last and len(clean_last) >= 2:
                params["lastName"] = clean_last
        elif clean_team and len(clean_team) >= 2:
            params["teamCode"] = clean_team
            params["teamName"] = clean_team

        if not params:
            return None

        async with sem:
            try:
                url = f"{BASE_API_URL}/editions/{event_id}/entrants"
                resp = await client.get(url, params=params)
                
                if resp.status_code != 200:
                    return None
                
                data = resp.json()
                raw_items = data.get("items", [])
                if not raw_items:
                    return None

                matched_entrants: List[EntrantResult] = []
                for item in raw_items:
                    item_first = str(item.get("firstName") or "").strip()
                    item_last = str(item.get("lastName") or "").strip()
                    item_team_name = str(item.get("teamName") or "").strip()
                    item_team_code = str(item.get("teamCode") or "").strip()
                    
                    if clean_team:
                        q_team = clean_team.lower()
                        code_match = q_team in item_team_code.lower()
                        name_match = q_team in item_team_name.lower()
                        if not (code_match or name_match):
                            continue

                    raw_course = item.get("courseName")
                    course_str = ""
                    if isinstance(raw_course, dict):
                        course_str = raw_course.get("it") or raw_course.get("en") or ""
                    elif isinstance(raw_course, str):
                        course_str = raw_course

                    full_name = f"{item_first} {item_last}".strip()

                    entrant = EntrantResult(
                        first_name=item_first,
                        last_name=item_last,
                        full_name=full_name,
                        bib=item.get("bib") or None,
                        year_of_birth=item.get("yearOfBirth"),
                        nationality=item.get("nationality"),
                        category=item.get("category"),
                        team_name=item_team_name or None,
                        team_code=item_team_code or None,
                        course_name=course_str or None
                    )
                    matched_entrants.append(entrant)

                if not matched_entrants:
                    return None

                slug = event.get("slug") or str(event_id)
                event_name = event.get("name") or "Gara ENDU"
                date_from = event.get("date", {}).get("from", "")
                date_formatted = format_iso_date(date_from)

                loc = event.get("location", {}) or {}
                city = loc.get("city")
                district = loc.get("district")
                if city and district:
                    location_formatted = f"{city} ({district})"
                elif city:
                    location_formatted = city
                elif district:
                    location_formatted = district
                else:
                    location_formatted = "Italia"

                event_url = f"https://www.endu.net/it/events/{slug}"
                verify_url = f"https://www.endu.net/it/events/{slug}/entry/verify"

                return EventMatch(
                    event_id=event_id,
                    name=event_name,
                    slug=slug,
                    event_url=event_url,
                    verify_url=verify_url,
                    date_from=date_from,
                    date_formatted=date_formatted,
                    city=city,
                    district=district,
                    location_formatted=location_formatted,
                    entrants=matched_entrants
                )

            except Exception:
                return None

    async def scan_events_stream(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        team_code: Optional[str] = None,
        months: int = 5,
        force_refresh: bool = False
    ) -> AsyncGenerator[Dict, None]:
        """Scansione live via SSE per gare future."""
        start_time = time.time()
        try:
            events, date_from, date_to = await self.get_road_running_events(
                months=months,
                force_refresh=force_refresh
            )
        except Exception as e:
            yield {
                "type": "error",
                "message": f"Errore nel recupero del calendario eventi ENDU: {str(e)}"
            }
            return

        total_events = len(events)
        yield {
            "type": "init",
            "total": total_events,
            "date_from": date_from,
            "date_to": date_to,
            "months": months
        }

        if total_events == 0:
            yield {
                "type": "complete",
                "total_scanned": 0,
                "matches_count": 0,
                "elapsed_seconds": round(time.time() - start_time, 2)
            }
            return

        checked_count = 0
        matches_count = 0
        sem = asyncio.Semaphore(self.concurrency_limit)

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=12.0) as client:
            tasks = [
                self.check_single_event(client, sem, ev, first_name, last_name, team_code)
                for ev in events
            ]

            for coro in asyncio.as_completed(tasks):
                result = await coro
                checked_count += 1

                if result is not None:
                    matches_count += 1
                    yield {
                        "type": "match",
                        "checked": checked_count,
                        "total": total_events,
                        "match": result.dict()
                    }
                else:
                    if checked_count % 5 == 0 or checked_count == total_events:
                        yield {
                            "type": "progress",
                            "checked": checked_count,
                            "total": total_events,
                            "matches_count": matches_count
                        }

        elapsed = round(time.time() - start_time, 2)
        yield {
            "type": "complete",
            "total_scanned": checked_count,
            "matches_count": matches_count,
            "elapsed_seconds": elapsed
        }

    async def scan_events(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        team_code: Optional[str] = None,
        months: int = 5,
        force_refresh: bool = False
    ) -> SearchResponse:
        """Scansione sincrona REST per gare future."""
        start_time = time.time()
        events, date_from, date_to = await self.get_road_running_events(
            months=months,
            force_refresh=force_refresh
        )

        matched_results: List[EventMatch] = []
        sem = asyncio.Semaphore(self.concurrency_limit)

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=12.0) as client:
            tasks = [
                self.check_single_event(client, sem, ev, first_name, last_name, team_code)
                for ev in events
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, EventMatch):
                    matched_results.append(res)

        matched_results.sort(key=lambda x: x.date_from)
        elapsed = round(time.time() - start_time, 2)

        return SearchResponse(
            success=True,
            total_events_scanned=len(events),
            matches_count=len(matched_results),
            date_from=date_from,
            date_to=date_to,
            elapsed_seconds=elapsed,
            results=matched_results
        )

    # =========================================================================
    # 2. FUNZIONALITÀ GARE PASSATE (RISULTATI E CLASSIFICHE)
    # =========================================================================

    async def get_past_running_events_with_results(
        self,
        months: int = 12,
        year: Optional[int] = None,
        force_refresh: bool = False
    ) -> Tuple[List[Dict], str, str]:
        """
        Recupera le manifestazioni passate di Corsa su Strada con classifiche digitali (results=dynamic).
        """
        today = datetime.date.today()
        if year:
            date_from_str = f"{year}-01-01"
            # Se l'anno è l'anno corrente, limita a oggi, altrimenti 31 dicembre
            date_to_str = today.strftime("%Y-%m-%d") if year == today.year else f"{year}-12-31"
        else:
            date_to_str = today.strftime("%Y-%m-%d")
            start_date = add_months(today, -months)
            date_from_str = start_date.strftime("%Y-%m-%d")

        now = time.time()
        lock = self._get_cache_lock()
        async with lock:
            if not force_refresh and self._cached_past_events is not None:
                if (now - self._past_cache_timestamp) < self.cache_ttl_seconds:
                    if self._past_cache_date_from == date_from_str and self._past_cache_date_to == date_to_str:
                        return self._cached_past_events, date_from_str, date_to_str

        collected_events: List[Dict] = []
        sequence_token: Optional[str] = None
        page_size = 500

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0) as client:
            while True:
                params = {
                    "dateFrom": date_from_str,
                    "dateTo": date_to_str,
                    "discipline": "road_running",
                    "results": "dynamic",
                    "pageSize": page_size,
                    "sort": "date.from"
                }
                if sequence_token:
                    params["sequenceToken"] = sequence_token

                response = await client.get(f"{BASE_API_URL}/events", params=params)
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                
                for item in items:
                    collected_events.append(item)

                total_items = data.get("totalItems", len(items))
                if len(items) < page_size or len(collected_events) >= total_items or not items:
                    break
                
                last_token = items[-1].get("sequenceToken")
                if not last_token or last_token == sequence_token:
                    break
                sequence_token = last_token

        async with lock:
            self._cached_past_events = collected_events
            self._past_cache_timestamp = time.time()
            self._past_cache_date_from = date_from_str
            self._past_cache_date_to = date_to_str

        return collected_events, date_from_str, date_to_str

    async def check_single_past_event_results(
        self,
        client: httpx.AsyncClient,
        sem: asyncio.Semaphore,
        event: Dict,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        team_code: Optional[str] = None
    ) -> Optional[PastEventResultMatch]:
        """
        Interroga la classifica ufficiale dell'evento passato per trovare tempi e piazzamenti.
        """
        event_id = event.get("id")
        if not event_id:
            return None

        clean_first = first_name.strip() if first_name else ""
        clean_last = last_name.strip() if last_name else ""
        clean_team = team_code.strip() if team_code else ""

        # Testo di ricerca principale da inviare all'API ENDU
        search_query = clean_last if clean_last else (clean_first if clean_first else clean_team)
        if not search_query or len(search_query) < 2:
            return None

        async with sem:
            try:
                # 1. Recupera le impostazioni di gara (races, categories, options)
                settings_url = f"{BASE_API_URL}/results/events/{event_id}/settings"
                settings_resp = await client.get(settings_url)
                if settings_resp.status_code != 200:
                    return None
                
                settings_data = settings_resp.json()
                edition_id = settings_data.get("editionId", event_id)
                races = settings_data.get("races", [])
                if not races:
                    return None

                matched_results: List[RaceResultItem] = []

                # 2. Per ciascuna gara (es. 10km, Mezza Maratona) interroga la classifica
                for rc in races:
                    race_id = rc.get("id")
                    race_name = rc.get("name") or "Gara"
                    
                    # Individua l'opzione 'Generale'
                    selected_opt_id = None
                    selected_cat_id = 0
                    for cat in rc.get("categories", []):
                        for opt in cat.get("options", []):
                            if opt.get("name", "").lower() in ["generale", "overall"] or opt.get("type") == "general":
                                selected_opt_id = opt.get("id")
                                selected_cat_id = cat.get("id", 0)
                                break
                        if selected_opt_id:
                            break
                    
                    # Fallback alla prima opzione disponibile
                    if not selected_opt_id and rc.get("categories"):
                        first_cat = rc["categories"][0]
                        if first_cat.get("options"):
                            selected_opt_id = first_cat["options"][0].get("id")
                            selected_cat_id = first_cat.get("id", 0)

                    if not selected_opt_id:
                        continue

                    # Chiama l'endpoint dei risultati filtrati per testo
                    results_url = f"{BASE_API_URL}/results"
                    res_params = {
                        "editionId": edition_id,
                        "raceId": race_id,
                        "categoryId": selected_cat_id,
                        "optionId": selected_opt_id,
                        "searchText": search_query
                    }
                    res = await client.get(results_url, params=res_params)
                    if res.status_code != 200:
                        continue

                    items = res.json().get("items", [])
                    for it in items:
                        it_first = str(it.get("firstName") or "").strip()
                        it_last = str(it.get("lastName") or "").strip()
                        cols = it.get("columns", {}) or {}
                        it_team = str(cols.get("teamName") or "").strip()

                        # Verifica corrispondenza nome
                        if clean_first:
                            if clean_first.lower() not in it_first.lower():
                                continue
                        if clean_last:
                            if clean_last.lower() not in it_last.lower():
                                continue
                        if clean_team:
                            if clean_team.lower() not in it_team.lower():
                                continue

                        full_name = f"{it_first} {it_last}".strip() or str(cols.get("name") or "")

                        result_item = RaceResultItem(
                            first_name=it_first,
                            last_name=it_last,
                            full_name=full_name,
                            race_name=race_name,
                            bib=str(cols.get("bib") or "") or None,
                            team_name=it_team or None,
                            category=str(cols.get("category") or "") or None,
                            gender=str(cols.get("gender") or "") or None,
                            year_of_birth=str(cols.get("yearOfBirth") or "") or None,
                            nationality=str(cols.get("nationality") or "") or None,
                            official_time=str(cols.get("officialTime") or "") or None,
                            real_time=str(cols.get("realTime") or "") or None,
                            gap_time=str(cols.get("gapTime") or "") or None,
                            absolute_position=str(cols.get("absolutePosition") or it.get("position") or "") or None,
                            category_position=str(cols.get("positionInCategory") or "") or None,
                            gender_position=str(cols.get("positionInGender") or "") or None
                        )
                        matched_results.append(result_item)

                if not matched_results:
                    return None

                slug = event.get("slug") or str(event_id)
                event_name = event.get("name") or "Gara ENDU"
                date_from = event.get("date", {}).get("from", "")
                date_formatted = format_iso_date(date_from)

                loc = event.get("location", {}) or {}
                city = loc.get("city")
                district = loc.get("district")
                if city and district:
                    location_formatted = f"{city} ({district})"
                elif city:
                    location_formatted = city
                elif district:
                    location_formatted = district
                else:
                    location_formatted = "Italia"

                event_url = f"https://www.endu.net/it/events/{slug}"
                results_url = f"https://www.endu.net/it/events/{slug}/results"

                return PastEventResultMatch(
                    event_id=event_id,
                    name=event_name,
                    slug=slug,
                    date_from=date_from,
                    date_formatted=date_formatted,
                    city=city,
                    district=district,
                    location_formatted=location_formatted,
                    results_url=results_url,
                    event_url=event_url,
                    results=matched_results
                )

            except Exception:
                return None

    async def scan_past_results_stream(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        team_code: Optional[str] = None,
        months: int = 12,
        year: Optional[int] = None,
        force_refresh: bool = False
    ) -> AsyncGenerator[Dict, None]:
        """Scansione live via SSE per risultati storici in gare passate."""
        start_time = time.time()
        try:
            events, date_from, date_to = await self.get_past_running_events_with_results(
                months=months,
                year=year,
                force_refresh=force_refresh
            )
        except Exception as e:
            yield {
                "type": "error",
                "message": f"Errore nel recupero del calendario gare passate: {str(e)}"
            }
            return

        total_events = len(events)
        yield {
            "type": "init",
            "total": total_events,
            "date_from": date_from,
            "date_to": date_to,
            "period": f"Anno {year}" if year else f"Ultimi {months} mesi"
        }

        if total_events == 0:
            yield {
                "type": "complete",
                "total_scanned": 0,
                "matches_count": 0,
                "elapsed_seconds": round(time.time() - start_time, 2)
            }
            return

        checked_count = 0
        matches_count = 0
        sem = asyncio.Semaphore(self.concurrency_limit)

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=12.0) as client:
            tasks = [
                self.check_single_past_event_results(client, sem, ev, first_name, last_name, team_code)
                for ev in events
            ]

            for coro in asyncio.as_completed(tasks):
                result = await coro
                checked_count += 1

                if result is not None:
                    matches_count += 1
                    yield {
                        "type": "match",
                        "checked": checked_count,
                        "total": total_events,
                        "match": result.dict()
                    }
                else:
                    if checked_count % 5 == 0 or checked_count == total_events:
                        yield {
                            "type": "progress",
                            "checked": checked_count,
                            "total": total_events,
                            "matches_count": matches_count
                        }

        elapsed = round(time.time() - start_time, 2)
        yield {
            "type": "complete",
            "total_scanned": checked_count,
            "matches_count": matches_count,
            "elapsed_seconds": elapsed
        }

    async def scan_past_results(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        team_code: Optional[str] = None,
        months: int = 12,
        year: Optional[int] = None,
        force_refresh: bool = False
    ) -> PastResultsSearchResponse:
        """Scansione sincrona REST per risultati storici."""
        start_time = time.time()
        events, date_from, date_to = await self.get_past_running_events_with_results(
            months=months,
            year=year,
            force_refresh=force_refresh
        )

        matched_results: List[PastEventResultMatch] = []
        sem = asyncio.Semaphore(self.concurrency_limit)

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=12.0) as client:
            tasks = [
                self.check_single_past_event_results(client, sem, ev, first_name, last_name, team_code)
                for ev in events
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, PastEventResultMatch):
                    matched_results.append(res)

        # Ordina dal più recente al meno recente
        matched_results.sort(key=lambda x: x.date_from, reverse=True)
        elapsed = round(time.time() - start_time, 2)

        return PastResultsSearchResponse(
            success=True,
            total_events_scanned=len(events),
            matches_count=len(matched_results),
            date_from=date_from,
            date_to=date_to,
            elapsed_seconds=elapsed,
            results=matched_results
        )
