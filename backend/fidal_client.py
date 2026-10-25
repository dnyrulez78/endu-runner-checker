"""
Client asincrono per l'interrogazione dell'archivio storico atleti FIDAL (Federazione Italiana di Atletica Leggera).
Permette di consultare la carriera agonistica ufficiale su strada (10km, Mezze Maratone, Maratone)
cronometrata da qualsiasi provider (TDS, ENDU, SDAM, WinningTime, Icron, ecc.).
"""

import re
import time
import urllib.parse
from typing import Dict, List, Optional, Tuple
import httpx
from pydantic import BaseModel, Field


class FidalRaceResult(BaseModel):
    year: int
    date: str  # es. "01/12"
    full_date: Optional[str] = None  # es. "01/12/2019"
    discipline: str  # es. "MARATONINA A", "Corsa strada Km 10"
    category: str  # es. "SM40"
    rank: str  # es. "282 su- 1"
    rank_cleaned: str  # es. "282°"
    time: str  # es. "1h44:39"
    city: str  # es. "Vicenza"
    notes: Optional[str] = None


class FidalPersonalBest(BaseModel):
    event: str  # es. "MARATONINA"
    track_type: str  # es. "Strada"
    time: str  # es. "1h26:37"
    year: str  # es. "2025"
    city: str  # es. "Treviso"


class FidalAthleteProfile(BaseModel):
    name: str
    surname: Optional[str] = None
    first_name: Optional[str] = None
    society: str
    birth_date: Optional[str] = None
    category: Optional[str] = None
    fidal_url: str
    personal_bests: List[FidalPersonalBest] = Field(default_factory=list)
    results: List[FidalRaceResult] = Field(default_factory=list)
    total_results: int = 0


class FidalSearchResponse(BaseModel):
    success: bool
    athletes_found: int
    athlete: Optional[FidalAthleteProfile] = None
    other_matching_athletes: List[Dict[str, str]] = Field(default_factory=list)
    elapsed_seconds: float
    message: Optional[str] = None


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8"
}


class FidalClient:
    def __init__(self, cache_ttl_seconds: int = 3600):
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, Tuple[float, FidalAthleteProfile]] = {}

    def _clean_rank(self, raw_rank: str) -> str:
        """Pulisce la stringa del piazzamento (es. '282 su- 1' -> '282°')."""
        raw = raw_rank.strip()
        m = re.match(r"^(\d+)", raw)
        if m:
            return f"{m.group(1)}°"
        return raw

    async def search_athlete(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        year: Optional[int] = None,
        city_or_race: Optional[str] = None
    ) -> FidalSearchResponse:
        """
        Cerca un atleta nell'archivio graduatorie FIDAL e ne estrae la carriera agonistica.
        """
        start_time = time.time()
        clean_last = last_name.strip()
        clean_first = first_name.strip() if first_name else ""

        if not clean_last:
            return FidalSearchResponse(
                success=False,
                athletes_found=0,
                elapsed_seconds=0.0,
                message="Specificare almeno il cognome dell'atleta."
            )

        # 1. Ricerca dell'atleta su result.php
        search_query = clean_last.upper()
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=12.0, follow_redirects=True) as client:
            try:
                res = await client.post(
                    "https://www.fidal.it/result.php",
                    data={"cerca": search_query, "submit": "Cerca"}
                )
                res.raise_for_status()
                html = res.text
            except Exception as e:
                return FidalSearchResponse(
                    success=False,
                    athletes_found=0,
                    elapsed_seconds=round(time.time() - start_time, 2),
                    message=f"Errore di connessione a fidal.it: {str(e)}"
                )

        # 2. Estrazione di tutti gli atleti trovati
        # Format: <a href="https://www.fidal.it/atleta/Nome-Cognome/token">
        matches = re.findall(
            r'href=["\'](https://www\.fidal\.it/atleta/([^/]+)/([^"\']+))["\']',
            html
        )

        if not matches:
            return FidalSearchResponse(
                success=True,
                athletes_found=0,
                elapsed_seconds=round(time.time() - start_time, 2),
                message=f"Nessun atleta trovato nei registri FIDAL per '{clean_last}'."
            )

        # Deduplica i link atleti
        unique_athletes: List[Tuple[str, str]] = []  # (url, slug_name)
        seen_urls = set()
        for full_url, slug_name, _ in matches:
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                display_name = slug_name.replace("-", " ")
                unique_athletes.append((full_url, display_name))

        # Filtra per nome se fornito
        chosen_url: Optional[str] = None
        if clean_first:
            first_lower = clean_first.lower()
            for full_url, display_name in unique_athletes:
                if first_lower in display_name.lower():
                    chosen_url = full_url
                    break

        if not chosen_url and unique_athletes:
            chosen_url = unique_athletes[0][0]

        # 3. Scarica e analizza la pagina dell'atleta
        now = time.time()
        cached_entry = self._cache.get(chosen_url)
        if cached_entry and (now - cached_entry[0] < self.cache_ttl_seconds):
            profile = cached_entry[1]
        else:
            profile = await self._fetch_athlete_profile(chosen_url)
            if profile:
                self._cache[chosen_url] = (now, profile)

        if not profile:
            return FidalSearchResponse(
                success=False,
                athletes_found=len(unique_athletes),
                elapsed_seconds=round(time.time() - start_time, 2),
                message="Impossibile estrarre la scheda atleta da FIDAL."
            )

        # 4. Applica eventuali filtri temporali o per città/gara
        filtered_results = profile.results
        if year:
            filtered_results = [r for r in filtered_results if r.year == year]

        if city_or_race:
            kw = city_or_race.strip().lower()
            filtered_results = [
                r for r in filtered_results
                if kw in r.city.lower() or kw in r.discipline.lower()
            ]

        # Clona il profilo con i risultati filtrati
        filtered_profile = FidalAthleteProfile(
            name=profile.name,
            surname=profile.surname,
            first_name=profile.first_name,
            society=profile.society,
            birth_date=profile.birth_date,
            category=profile.category,
            fidal_url=profile.fidal_url,
            personal_bests=profile.personal_bests,
            results=filtered_results,
            total_results=len(filtered_results)
        )

        other_athletes = [
            {"name": name, "url": url}
            for url, name in unique_athletes
            if url != chosen_url
        ]

        return FidalSearchResponse(
            success=True,
            athletes_found=len(unique_athletes),
            athlete=filtered_profile,
            other_matching_athletes=other_athletes,
            elapsed_seconds=round(time.time() - start_time, 2)
        )

    async def _fetch_athlete_profile(self, url: str) -> Optional[FidalAthleteProfile]:
        """Scarica e analizza la pagina HTML ufficiale della scheda atleta FIDAL."""
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=12.0) as client:
            try:
                res = await client.get(url)
                res.raise_for_status()
                html = res.text
            except Exception:
                return None

        # 1. Nome Atleta
        name_match = re.search(r'<h1>(.*?)</h1>', html)
        name = name_match.group(1).strip() if name_match else "Atleta FIDAL"

        # 2. Società di tesseramento
        soc_match = re.search(r'<span><a[^>]*>(.*?)</a></span>', html)
        society = soc_match.group(1).strip() if soc_match else "Non specificata"

        # 3. Data di nascita
        birth_match = re.search(r'<br>(\d{2}-\d{2}-\d{4})', html)
        birth_date = birth_match.group(1).strip() if birth_match else None

        # 4. Primati Personali (Table 6)
        personal_bests: List[FidalPersonalBest] = []
        pb_match = re.search(
            r'<h3>Primati Personali</h3>.*?<table[^>]*>(.*?)</table>',
            html,
            re.DOTALL | re.IGNORECASE
        )
        if not pb_match:
            # Cerca tabella con 'Prestazione' e 'Gara'
            all_tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
            for t in all_tables:
                if "Primati" in t or ("Gara" in t and "Prestazione" in t and "Vento" in t):
                    pb_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.DOTALL)
                    for r in pb_rows:
                        tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
                        t_clean = [re.sub(r'<[^>]+>', '', td).strip() for td in tds]
                        if len(t_clean) >= 6:
                            personal_bests.append(FidalPersonalBest(
                                event=t_clean[0],
                                track_type=t_clean[1],
                                time=t_clean[2],
                                year=t_clean[4],
                                city=t_clean[5]
                            ))
                    break

        # 5. Risultati Agonistici Ufficiali (Tutte le tabelle di specialità)
        results: List[FidalRaceResult] = []
        parts = re.split(r'<table[^>]*>', html)
        for i in range(1, len(parts)):
            prev_chunk = parts[i - 1]
            table_content = parts[i].split('</table>')[0]

            headings = re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', prev_chunk)
            discipline = headings[-1].strip() if headings else "Gara"
            if discipline in ["Condividi con", "In Squadra Con", "Partner", "Mappa del sito", "Primati Personali"]:
                continue

            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_content, re.DOTALL)
            for r in rows:
                tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
                td_texts = [re.sub(r'<[^>]+>', '', td).strip() for td in tds]
                # Columns: ['Anno', 'Data', 'Tipo', 'Cr.', 'Cat.', 'Piazz.', 'Prestaz.', 'Vento', 'Città', '&nbsp;']
                if len(td_texts) >= 9 and td_texts[0].isdigit():
                    yr = int(td_texts[0])
                    date_day_month = td_texts[1]
                    full_date = f"{date_day_month}/{yr}" if "/" in date_day_month else str(yr)
                    raw_rank = td_texts[5]

                    results.append(FidalRaceResult(
                        year=yr,
                        date=date_day_month,
                        full_date=full_date,
                        discipline=discipline,
                        category=td_texts[4],
                        rank=raw_rank,
                        rank_cleaned=self._clean_rank(raw_rank),
                        time=td_texts[6],
                        city=td_texts[8]
                    ))

        # Ordina dal più recente al più vecchio
        results.sort(key=lambda x: (x.year, x.date), reverse=True)

        return FidalAthleteProfile(
            name=name,
            society=society,
            birth_date=birth_date,
            fidal_url=url,
            personal_bests=personal_bests,
            results=results,
            total_results=len(results)
        )
