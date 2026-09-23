from pydantic import BaseModel
from typing import Literal, Optional

class FindRequest(BaseModel):
    city: str
    event_date: str          # "2026-11-14"
    event_format: str
    category: str
    budget_kzt: int
    duration_hours: Optional[int] = None
    language: Optional[str] = None

class Candidate(BaseModel):
    id: str
    name: str
    category: str
    city: str
    price_from_kzt: int
    explanation: str
    synthetic: bool = False

class FindResponse(BaseModel):
    status: Literal["ok", "no_category_in_city", "no_match"]
    candidates: list[Candidate] = []
    excluded_count: int = 0
    excluded_reasons: list[str] = []
