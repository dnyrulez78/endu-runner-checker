"""
Client asincrono per l'interrogazione delle manifestazioni, degli iscritti e dell'archivio storico
del Trail Running sulla piattaforma Wedosport (wedosport.net).
Fornisce:
1. Scansione delle iscrizioni future alle gare Trail / Skyrunning aperte.
2. Interrogazione dell'archivio carriera e risultati storici dal 2004 ad oggi.
"""

import asyncio
from datetime import date, datetime, timedelta
import logging
import re
import time
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import httpx

from backend.models import (
    CalendarStatusResponse,
    EntrantResult,
    EventMatch,
    SearchResponse,
    WedosportAthleteProfile,
    WedosportCareerSearchResponse,
    WedosportRaceResult,
)

logger = logging.getLogger("endu_tool.wedosport")

WEDOSPORT_BASE_URL = "https://www.wedosport.net"
WEDOSPORT_ISCRIZIONI_URL = f"{WEDOSPORT_BASE_URL}/iscrizioni.cfm"
WEDOSPORT_RICERCA_GARE_URL = f"{WEDOSPORT_BASE_URL}/ricerca_gare.cfm"
WEDOSPORT_DETTAGLIO_ATLETA_URL = f"{WEDOSPORT_BASE_URL}/ricerca_atleta_dettaglio.cfm"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Referer": WEDOSPORT_BASE_URL
}

MONTH_MAP_IT = {
    "gennaio": 1, "gen": 1,
    "febbraio": 2, "feb": 2,
    "marzo": 3, "mar": 3,
    "aprile": 4, "apr": 4,
    "maggio": 5, "mag": 5,
    "giugno": 6, "giu": 6,
    "luglio": 7, "lug": 7,
    "agosto": 8, "ago": 8,
    "settembre": 9, "set": 9,
    "ottobre": 10, "ott": 10,
    "novembre": 11, "nov": 11,
    "dicembre": 12, "dic": 12
}

MONTH_NAMES_SHORT = {
    1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "Mag", 6: "Giu", 7: "Lug", 8: "Ago",
    9: "Set", 10: "Ott", 11: "Nov", 12: "Dic"
}


def parse_wedosport_date(date_str: Optional[str]) -> Optional[date]:
    """Interpreta stringhe di data Wedosport (es. 'Sabato, 31 Ottobre 2026' o '31/10/2026')."""
    if not date_str:
        return None
    clean = date_str.strip().lower()

    # Formato DD/MM/YYYY
    m1 = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", clean)
    if m1:
        try:
            return date(int(m1.group(3)), int(m1.group(2)), int(m1.group(1)))
        except ValueError:
            pass

    # Formato italiano esteso: '31 ottobre 2026'
    m2 = re.search(r"(\d{1,2})\s+([a-zàèéìòù]+)\s+(\d{4})", clean)
    if m2:
        day = int(m2.group(1))
        month_name = m2.group(2).strip()
        year = int(m2.group(3))
        month = MONTH_MAP_IT.get(month_name)
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass

    return None


def format_wedosport_date(d: date) -> str:
    """Formatta un oggetto date in GG Mmm AAAA (es. 31 Ott 2026)."""
    month_name = MONTH_NAMES_SHORT.get(d.month, str(d.month))
    return f"{d.day:02d} {month_name} {d.year}"


class WedosportClient:
    """Client per la consultazione delle gare Trail, iscrizioni future e palmarès su Wedosport."""

    def __init__(self, cache_ttl_seconds: int = 3600, max_concurrency: int = 6):
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

    async def get_open_events(
        self,
        months: int = 5,
        exact_date: Optional[str] = None,
        event_name: Optional[str] = None,
        force_refresh: bool = False
    ) -> Tuple[List[Dict], str, str]:
        """
        Recupera e memorizza in cache tutte le manifestazioni trail aperte di Wedosport.
        """
        async with self._cache_lock:
            if force_refresh or not self.is_cache_valid():
                logger.info("Aggiornamento del calendario manifestazioni da Wedosport...")
                async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=20.0) as client:
                    resp = await client.get(WEDOSPORT_ISCRIZIONI_URL, follow_redirects=True)
                    resp.raise_for_status()
                    html_text = resp.text

                blocks = re.findall(
                    r'<div class="row riga_volantino row_eq_height">(.*?)</div>\s*</div>\s*</div>',
                    html_text,
                    re.DOTALL
                )

                parsed_events = []
                for b in blocks:
                    slug_m = re.search(
                        r'href=["\'](?:https://www\.wedosport\.net)?/([^"\'/\?]+)["\'][^>]*>\s*<img[^>]*class="[^"]*immagine-volantino',
                        b
                    )
                    if not slug_m:
                        continue
                    slug = slug_m.group(1).strip()

                    name_m = re.search(r'class="pannello-metro-header[^"]*"[^>]*>\s*<b[^>]*>(.*?)</b>', b, re.DOTALL)
                    name = re.sub(r'<[^>]+>', '', name_m.group(1)).strip() if name_m else slug

                    date_m = re.search(r'class="volantino-iscrizioni-data[^"]*"[^>]*>.*?<h3[^>]*>(.*?)</h3>', b, re.DOTALL)
                    raw_date = re.sub(r'<[^>]+>', '', date_m.group(1)).strip() if date_m else ""

                    loc_m = re.search(r'google\.it/maps/place/([^"\']+)["\']', b)
                    location = loc_m.group(1).strip() if loc_m else ""

                    has_public_list = (
                        (f"lista_iscritti.cfm?code={slug}" in b) or
                        (f"/lista-iscritti/{slug}" in b) or
                        ("elenco_iscritti.png" in b)
                    )

                    ev_date = parse_wedosport_date(raw_date)

                    parsed_events.append({
                        "slug": slug,
                        "name": name,
                        "raw_date": raw_date,
                        "parsed_date": ev_date,
                        "location": location,
                        "has_public_list": has_public_list
                    })

                self._events_cache = parsed_events
                self._cache_timestamp = time.time()
                logger.info(f"Calendario Wedosport aggiornato: {len(parsed_events)} gare trovate ({len([e for e in parsed_events if e['has_public_list']])} con lista iscritti pubblica).")

        all_events = self._events_cache or []
        today = date.today()
        end_date = today + timedelta(days=int(months * 30.5))

        exact_filter_date: Optional[date] = None
        if exact_date:
            try:
                exact_filter_date = date.fromisoformat(exact_date.strip())
            except ValueError:
                exact_filter_date = parse_wedosport_date(exact_date.strip())

        filtered: List[Dict] = []
        for ev in all_events:
            ev_date = ev.get("parsed_date")

            # Filtro temporale standard
            if ev_date:
                if not (today <= ev_date <= end_date):
                    if not (exact_filter_date and ev_date == exact_filter_date):
                        continue
            # Filtro data esatta
            if exact_filter_date and ev_date and ev_date != exact_filter_date:
                continue

            # Filtro nome manifestazione o città
            if event_name:
                kw = event_name.strip().lower()
                desc = str(ev.get("name") or "").lower()
                loc = str(ev.get("location") or "").lower()
                slug = str(ev.get("slug") or "").lower()
                if kw not in desc and kw not in loc and kw not in slug:
                    continue

            filtered.append(dict(ev))

        # Ordina cronologicamente
        filtered.sort(key=lambda x: x.get("parsed_date") or date(2099, 12, 31))

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
        """Verifica se l'atleta o la società è presente nella lista iscritti della gara Wedosport."""
        if not event.get("has_public_list"):
            return None

        slug = event.get("slug")
        clean_first = first_name.strip().lower() if first_name else ""
        clean_last = last_name.strip().lower() if last_name else ""
        clean_team = team_code.strip().lower() if team_code else ""

        url = f"{WEDOSPORT_BASE_URL}/lista-iscritti/{slug}"

        async with sem:
            try:
                resp = await client.get(url, timeout=14.0, follow_redirects=True)
                if resp.status_code != 200:
                    return None

                html_text = resp.text
                if "<table" not in html_text:
                    return None

                # Estrai intestazione per mappare le colonne dinamicamente
                thead_match = re.search(r'<thead[^>]*>(.*?)</thead>', html_text, re.DOTALL)
                col_map = {
                    "last_name": -1,
                    "first_name": -1,
                    "team": -1,
                    "bib": -1,
                    "course": -1,
                    "provenienza": -1,
                    "sex": -1
                }

                if thead_match:
                    th_cells = [
                        re.sub(r'<[^>]+>', '', c).strip().lower()
                        for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', thead_match.group(1), re.DOTALL)
                    ]
                    for idx, th in enumerate(th_cells):
                        if "cognome" in th:
                            col_map["last_name"] = idx
                        elif "nome" in th:
                            col_map["first_name"] = idx
                        elif any(k in th for k in ["societ", "squadra"]):
                            col_map["team"] = idx
                        elif "pettorale" in th:
                            col_map["bib"] = idx
                        elif any(k in th for k in ["distanza", "gara", "percorso"]):
                            col_map["course"] = idx
                        elif any(k in th for k in ["provenienza", "nazionalit"]):
                            col_map["provenienza"] = idx
                        elif "sex" in th or "sesso" in th:
                            col_map["sex"] = idx

                # Estrai tutte le righe <tr> del <tbody> o della tabella
                table_match = re.search(r'<table[^>]*>(.*?)</table>', html_text, re.DOTALL)
                if not table_match:
                    return None

                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_match.group(1), re.DOTALL)
                matched_entrants: List[EntrantResult] = []

                for r_row in rows:
                    cells = [
                        re.sub(r'<[^>]+>', '', c).strip()
                        for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r_row, re.DOTALL)
                    ]
                    if not cells or len(cells) < 3:
                        continue

                    # Estrai campi tramite col_map se valido, altrimenti fallback posizionale
                    if col_map["last_name"] != -1 and col_map["last_name"] < len(cells):
                        p_last = cells[col_map["last_name"]]
                    else:
                        p_last = cells[1] if len(cells) > 1 else ""

                    if col_map["first_name"] != -1 and col_map["first_name"] < len(cells):
                        p_first = cells[col_map["first_name"]]
                    else:
                        p_first = cells[2] if len(cells) > 2 else ""

                    if col_map["team"] != -1 and col_map["team"] < len(cells):
                        p_team = cells[col_map["team"]]
                    else:
                        p_team = cells[4] if len(cells) > 4 else ""

                    p_bib = cells[col_map["bib"]] if (col_map["bib"] != -1 and col_map["bib"] < len(cells)) else None
                    if p_bib and p_bib in ["&nbsp;", "0", ""]:
                        p_bib = None

                    p_course = cells[col_map["course"]] if (col_map["course"] != -1 and col_map["course"] < len(cells)) else None
                    if p_course and p_course in ["&nbsp;", ""]:
                        p_course = None

                    p_prov = cells[col_map["provenienza"]] if (col_map["provenienza"] != -1 and col_map["provenienza"] < len(cells)) else None

                    # Verifica filtri
                    if clean_last and clean_last not in p_last.lower():
                        continue
                    if clean_first and clean_first not in p_first.lower():
                        continue
                    if clean_team and clean_team not in p_team.lower():
                        continue

                    full_name = f"{p_first.title()} {p_last.upper()}".strip()
                    matched_entrants.append(
                        EntrantResult(
                            first_name=p_first.title(),
                            last_name=p_last.upper(),
                            full_name=full_name,
                            bib=p_bib,
                            team_name=p_team or None,
                            nationality=p_prov or None,
                            course_name=p_course or None
                        )
                    )

                if not matched_entrants:
                    return None

                ev_date = event.get("parsed_date") or date.today()
                date_from_iso = ev_date.isoformat()
                date_formatted = format_wedosport_date(ev_date)

                event_url = f"{WEDOSPORT_BASE_URL}/{slug}"
                verify_url = f"{WEDOSPORT_BASE_URL}/lista-iscritti/{slug}"

                return EventMatch(
                    event_id=f"wedo-{slug}",
                    name=event.get("name") or slug,
                    slug=slug,
                    event_url=event_url,
                    verify_url=verify_url,
                    date_from=date_from_iso,
                    date_formatted=date_formatted,
                    location_formatted=event.get("location") or "Italia",
                    source="WEDOSPORT",
                    entrants=matched_entrants
                )

            except Exception as e:
                logger.debug(f"Errore controllo iscritti Wedosport evento {slug}: {e}")
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
        """Esegue la scansione completa di tutti gli eventi Wedosport con lista iscritti attiva."""
        start_time = time.time()
        events, date_from, date_to = await self.get_open_events(
            months=months,
            exact_date=exact_date,
            event_name=event_name,
            force_refresh=force_refresh
        )

        public_events = [ev for ev in events if ev.get("has_public_list")]

        sem = asyncio.Semaphore(self.max_concurrency)
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0) as client:
            tasks = [
                self.check_event_entrants(client, sem, ev, first_name, last_name, team_code)
                for ev in public_events
            ]
            results_or_none = await asyncio.gather(*tasks)

        matches = [m for m in results_or_none if m is not None]
        matches.sort(key=lambda m: m.date_from)

        return SearchResponse(
            success=True,
            total_events_scanned=len(public_events),
            matches_count=len(matches),
            date_from=date_from,
            date_to=date_to,
            elapsed_seconds=round(time.time() - start_time, 2),
            results=matches
        )

    async def search_athlete_career(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        year: Optional[int] = None,
        race_name: Optional[str] = None
    ) -> WedosportCareerSearchResponse:
        """
        Interroga l'archivio storico di Wedosport (2004 - Oggi) ed estrae il palmarès dell'atleta.
        """
        start_time = time.time()
        clean_last = last_name.strip()
        clean_first = first_name.strip() if first_name else ""

        if not clean_last:
            return WedosportCareerSearchResponse(
                success=False,
                athletes_found=0,
                elapsed_seconds=0.0,
                message="Specificare il cognome dell'atleta per la ricerca su Wedosport."
            )

        headers = {
            **DEFAULT_HEADERS,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": WEDOSPORT_RICERCA_GARE_URL
        }

        try:
            async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
                # 1. Ricerca anagrafica candidati su ricerca_gare.cfm (valoreRicerca=2 -> Atleta)
                p_search = {
                    "valoreGare": clean_last,
                    "valoreRicerca": "2"
                }
                resp = await client.post(WEDOSPORT_RICERCA_GARE_URL, data=p_search, follow_redirects=True)
                resp.raise_for_status()
                html_candidates = resp.text

                button_regex = re.findall(r'<button[^>]*class=["\']atleta["\'][^>]*>.*?</button>', html_candidates, re.DOTALL)
                if not button_regex:
                    return WedosportCareerSearchResponse(
                        success=True,
                        athletes_found=0,
                        elapsed_seconds=round(time.time() - start_time, 2),
                        message=f"Nessun atleta trovato con cognome '{clean_last}' nell'archivio Wedosport."
                    )

                candidates = []
                for b_raw in button_regex:
                    b_codice = re.search(r'data-codice=["\']([^"\']*)["\']', b_raw)
                    b_num = re.search(r'data-numero=["\']([^"\']*)["\']', b_raw)
                    b_anno = re.search(r'data-anno=["\']([^"\']*)["\']', b_raw)
                    b_nome = re.sub(r'<[^>]+>', '', b_raw).strip()

                    cod = b_codice.group(1) if b_codice else ""
                    num = int(b_num.group(1)) if (b_num and b_num.group(1).isdigit()) else 0
                    ann = int(b_anno.group(1)) if (b_anno and b_anno.group(1).isdigit()) else None

                    candidates.append({
                        "name": b_nome,
                        "athlete_code": cod,
                        "total_races": num,
                        "birth_year": ann
                    })

                # Filtra per cognome e (se fornito) per nome
                matching = []
                for c in candidates:
                    c_name_lower = c["name"].lower()
                    if clean_last.lower() in c_name_lower:
                        if not clean_first or clean_first.lower() in c_name_lower:
                            matching.append(c)

                if not matching:
                    # Se il filtro nome è troppo stretto, prendiamo i candidati che hanno almeno il cognome
                    matching = [c for c in candidates if clean_last.lower() in c["name"].lower()]

                if not matching:
                    return WedosportCareerSearchResponse(
                        success=True,
                        athletes_found=0,
                        elapsed_seconds=round(time.time() - start_time, 2),
                        message=f"Nessun atleta corrispondente a '{clean_first} {clean_last}' trovato su Wedosport."
                    )

                # Seleziona il candidato principale (quello con più gare disputate o match più preciso)
                primary = matching[0]
                if clean_first:
                    for c in matching:
                        if clean_first.lower() in c["name"].lower():
                            primary = c
                            break

                # 2. Richiedi la scheda dettaglio gare dell'atleta
                p_det = {
                    "nome": primary["name"],
                    "codice_atleta": primary["athlete_code"],
                    "numero": str(primary["total_races"]),
                    "anno": str(primary["birth_year"] or "")
                }
                resp_det = await client.post(WEDOSPORT_DETTAGLIO_ATLETA_URL, data=p_det, follow_redirects=True)
                resp_det.raise_for_status()
                html_det = resp_det.text

                # Estrai righe della tabella palmarès
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_det, re.DOTALL)
                race_results: List[WedosportRaceResult] = []
                society_detected: Optional[str] = None

                for r_row in rows:
                    cells = [
                        re.sub(r'<[^>]+>', '', c).strip()
                        for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r_row, re.DOTALL)
                    ]
                    # Salta riga intestazione
                    if not cells or "Sport" in cells[0] or len(cells) < 7:
                        continue

                    # Colonne: Sport, Data, Nome, Distanza, km, Posizione, Tempo, Società
                    sport = cells[0] or "Trail Running"
                    r_date = cells[1] or ""
                    r_name = cells[2] or ""
                    dist_name = cells[3] if len(cells) > 3 else ""
                    dist_km = cells[4] if len(cells) > 4 else ""
                    rank = cells[5] if len(cells) > 5 else ""
                    r_time = cells[6] if len(cells) > 6 else ""
                    team = cells[7] if len(cells) > 7 else None

                    if team and not society_detected:
                        society_detected = team

                    # Link classifica
                    link_m = re.search(r'href=["\']([^"\']*classifica[^"\']*)["\']', r_row)
                    classifica_url = None
                    if link_m:
                        raw_link = link_m.group(1).strip()
                        if raw_link.startswith("http"):
                            classifica_url = raw_link
                        else:
                            classifica_url = f"{WEDOSPORT_BASE_URL}/{raw_link.lstrip('/')}"

                    # Anno solare
                    r_year = None
                    if "/" in r_date:
                        parts = r_date.split("/")
                        if len(parts) == 3 and parts[2].isdigit():
                            r_year = int(parts[2])

                    # Filtro Anno se specificato
                    if year and r_year and r_year != year:
                        continue

                    # Filtro Nome Gara se specificato
                    if race_name:
                        rn_kw = race_name.strip().lower()
                        if rn_kw not in r_name.lower() and rn_kw not in dist_name.lower():
                            continue

                    rank_cleaned = f"{rank}°" if (rank and rank.isdigit()) else rank

                    race_results.append(
                        WedosportRaceResult(
                            sport=sport,
                            date=r_date,
                            year=r_year,
                            race_name=r_name,
                            distance_name=dist_name,
                            distance_km=dist_km,
                            rank=rank,
                            rank_cleaned=rank_cleaned,
                            time=r_time,
                            team=team or None,
                            classifica_url=classifica_url
                        )
                    )

                profile = WedosportAthleteProfile(
                    name=primary["name"],
                    athlete_code=primary["athlete_code"] or None,
                    birth_year=primary["birth_year"],
                    society=society_detected,
                    total_races=len(race_results),
                    results=race_results
                )

                other_list = [c for c in matching if c["name"] != primary["name"]]

                return WedosportCareerSearchResponse(
                    success=True,
                    athletes_found=len(matching),
                    athlete=profile,
                    other_candidates=other_list,
                    elapsed_seconds=round(time.time() - start_time, 2)
                )

        except Exception as e:
            logger.error(f"Errore nella ricerca carriera Wedosport per '{clean_last}': {e}", exc_info=True)
            return WedosportCareerSearchResponse(
                success=False,
                athletes_found=0,
                elapsed_seconds=round(time.time() - start_time, 2),
                message=f"Errore durante l'interrogazione di Wedosport: {str(e)}"
            )
