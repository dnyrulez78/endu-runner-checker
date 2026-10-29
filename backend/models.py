from typing import List, Optional, Union
from pydantic import BaseModel, Field


class EntrantResult(BaseModel):
    """Rappresenta un atleta iscritto a una gara futura."""
    first_name: str = Field(..., description="Nome atleta")
    last_name: str = Field(..., description="Cognome atleta")
    full_name: str = Field(..., description="Nome e cognome formattati")
    bib: Optional[str] = Field(None, description="Numero di pettorale")
    year_of_birth: Optional[int] = Field(None, description="Anno di nascita")
    nationality: Optional[str] = Field(None, description="Nazionalità")
    category: Optional[str] = Field(None, description="Categoria di appartenenza")
    team_name: Optional[str] = Field(None, description="Nome società sportiva")
    team_code: Optional[str] = Field(None, description="Codice società")
    course_name: Optional[str] = Field(None, description="Distanza / Nome percorso")


class EventMatch(BaseModel):
    """Rappresenta una gara futura in cui è presente l'atleta."""
    event_id: Union[int, str] = Field(..., description="ID identificativo univoco evento")
    name: str = Field(..., description="Nome ufficiale della manifestazione")
    slug: str = Field(..., description="Slug URL della manifestazione")
    event_url: str = Field(..., description="Link diretto alla pagina ufficiale")
    verify_url: str = Field(..., description="Link diretto alla pagina di verifica iscrizione")
    date_from: str = Field(..., description="Data/ora di inizio evento (ISO)")
    date_formatted: str = Field(..., description="Data formattata (GG Mmm AAAA)")
    city: Optional[str] = Field(None, description="Città ospitante")
    district: Optional[str] = Field(None, description="Provincia o Regione")
    location_formatted: str = Field(..., description="Località formattata")
    source: str = Field("ENDU", description="Piattaforma: ENDU, ICRON o WEDOSPORT")
    entrants: List[EntrantResult] = Field(default_factory=list, description="Elenco atleti corrispondenti")


class SearchResponse(BaseModel):
    """Risposta aggregata per la route API di ricerca iscrizioni future."""
    success: bool
    total_events_scanned: int
    matches_count: int
    date_from: str
    date_to: str
    elapsed_seconds: float
    results: List[EventMatch]
    message: Optional[str] = None


class CalendarStatusResponse(BaseModel):
    """Stato della cache locale del calendario gare running."""
    is_cached: bool
    total_events: int
    total_endu_events: Optional[int] = None
    total_icron_events: Optional[int] = None
    total_wedosport_events: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    cached_at: Optional[str] = None
    ttl_seconds_remaining: Optional[int] = None
    author_mode: Optional[bool] = False



# --- Modelli per la Ricerca Risultati Storici (Gare Passate) ---

class RaceResultItem(BaseModel):
    """Rappresenta il piazzamento e tempo di un atleta in una gara passata."""
    first_name: str
    last_name: str
    full_name: str
    race_name: str
    bib: Optional[str] = None
    team_name: Optional[str] = None
    category: Optional[str] = None
    gender: Optional[str] = None
    year_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    official_time: Optional[str] = None
    real_time: Optional[str] = None
    gap_time: Optional[str] = None
    absolute_position: Optional[str] = None
    category_position: Optional[str] = None
    gender_position: Optional[str] = None


class PastEventResultMatch(BaseModel):
    """Rappresenta una gara passata in cui sono stati trovati i risultati dell'atleta."""
    event_id: int
    name: str
    slug: str
    date_from: str
    date_formatted: str
    city: Optional[str] = None
    district: Optional[str] = None
    location_formatted: str
    results_url: str
    event_url: str
    results: List[RaceResultItem] = Field(default_factory=list)


class PastResultsSearchResponse(BaseModel):
    """Risposta aggregata per la ricerca dei risultati storici."""
    success: bool
    total_events_scanned: int
    matches_count: int
    date_from: str
    date_to: str
    elapsed_seconds: float
    results: List[PastEventResultMatch]
    message: Optional[str] = None


# --- Modelli per l'Archivio Trail Running (Wedosport) ---

class WedosportRaceResult(BaseModel):
    """Rappresenta una gara trail disputata dall'atleta su Wedosport (dal 2004 a oggi)."""
    sport: str = Field("Trail Running", description="Disciplina (Trail Running, Skyrunning, ecc.)")
    date: str = Field(..., description="Data della gara (GG/MM/AAAA)")
    year: Optional[int] = Field(None, description="Anno solare")
    race_name: str = Field(..., description="Nome della manifestazione")
    distance_name: str = Field("", description="Nome percorso / distanza")
    distance_km: str = Field("", description="Chilometraggio")
    rank: str = Field("", description="Posizione assoluta")
    rank_cleaned: str = Field("", description="Posizione formattata (es. 88°)")
    time: str = Field(..., description="Tempo finale")
    team: Optional[str] = Field(None, description="Società sportiva")
    classifica_url: Optional[str] = Field(None, description="Link alla classifica ufficiale")


class WedosportAthleteProfile(BaseModel):
    """Profilo dell'atleta estratto dall'archivio gare Wedosport."""
    name: str = Field(..., description="Nome e cognome dell'atleta")
    athlete_code: Optional[str] = Field(None, description="Codice univoco atleta")
    birth_year: Optional[int] = Field(None, description="Anno di nascita")
    society: Optional[str] = Field(None, description="Società di appartenenza")
    total_races: int = Field(0, description="Numero totale di gare disputate")
    results: List[WedosportRaceResult] = Field(default_factory=list, description="Elenco gare disputate")


class WedosportCareerSearchResponse(BaseModel):
    """Risposta per la ricerca carriera e risultati trail su Wedosport."""
    success: bool
    athletes_found: int
    athlete: Optional[WedosportAthleteProfile] = None
    other_candidates: List[dict] = Field(default_factory=list)
    elapsed_seconds: float
    message: Optional[str] = None

