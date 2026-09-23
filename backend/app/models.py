from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

class FindRequest(BaseModel):
    city: str = Field(min_length=1)
    event_date: date
    event_format: str = Field(min_length=1)
    category: str = Field(min_length=1)
    budget_kzt: int = Field(ge=0)
    duration_hours: Optional[float] = Field(default=None, gt=0)
    language: Optional[str] = None

    @field_validator("city", "category", "event_format", "language")
    @classmethod
    def strip_text(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Must not be blank")
        return value

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value):
        if value is None:
            return value
        aliases = {"ru": "русский", "kz": "казахский", "kk": "казахский", "en": "английский"}
        return aliases.get(value.casefold(), value.casefold())

class Contractor(BaseModel):
    id: str
    name: str
    categories: list[str]
    city: str
    description: str = Field(min_length=1)
    price_from_kzt: int = Field(ge=0)
    languages: list[str] = Field(default_factory=list)
    max_hours: Optional[float] = Field(default=None, gt=0)
    busy_dates: list[date]
    event_formats: list[str] = Field(default_factory=list)
    price_imputed: bool = False
    city_imputed: bool = False
    synthetic: bool = False

class Candidate(BaseModel):
    id: str
    name: str
    category: str
    city: str
    price_from_kzt: int
    explanation: str
    synthetic: bool = False
    price_imputed: bool = False
    city_imputed: bool = False

class FindResponse(BaseModel):
    status: Literal["ok", "no_category_in_city", "no_match"]
    candidates: list[Candidate] = Field(default_factory=list)
    excluded_count: int = 0
    excluded_reasons: list[str] = Field(default_factory=list)
