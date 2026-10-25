from typing import List, Optional
from pydantic import BaseModel, Field


class EntrantResult(BaseModel):
    """Rappresenta un atleta iscritto a una gara."""
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
    """Rappresenta una gara in cui è stata trovata la presenza dell'atleta o della squadra."""
    event_id: int = Field(..., description="ID identificativo univoco evento ENDU")
    name: str = Field(..., description="Nome ufficiale della manifestazione")
    slug: str = Field(..., description="Slug URL della manifestazione")
    event_url: str = Field(..., description="Link diretto alla pagina ufficiale ENDU")
    verify_url: str = Field(..., description="Link diretto alla pagina di verifica iscrizione ENDU")
    date_from: str = Field(..., description="Data/ora di inizio evento (ISO)")
    date_formatted: str = Field(..., description="Data formattata (GG/MM/AAAA)")
    city: Optional[str] = Field(None, description="Città ospitante")
    district: Optional[str] = Field(None, description="Provincia")
    location_formatted: str = Field(..., description="Località formattata")
    entrants: List[EntrantResult] = Field(default_factory=list, description="Elenco atleti corrispondenti")


class SearchResponse(BaseModel):
    """Risposta aggregata per la route API di ricerca."""
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
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    cached_at: Optional[str] = None
    ttl_seconds_remaining: Optional[int] = None
