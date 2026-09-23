"""Initialize once at startup, then pass the filtered dataset to rank_and_explain."""
from __future__ import annotations

from functools import lru_cache
from threading import RLock
from typing import Any

import numpy as np

from app.models import FindRequest

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _normalize(vectors):
    matrix = np.asarray(vectors, dtype=float)
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        raise ValueError("Encoder must return a finite two-dimensional matrix")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return np.divide(matrix, norms, out=np.zeros_like(matrix), where=norms != 0)


class Ranker:
    def __init__(self, contractors: list[dict], model: Any = None):
        if model is None:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(MODEL_NAME)
        self.model = model
        self._lock = RLock()
        self.descriptions = {}
        for c in contractors:
            key = str(c["id"])
            if key in self.descriptions:
                raise ValueError(f"Duplicate contractor id: {key}")
            description = c["description"]
            if not isinstance(description, str) or not description.strip():
                raise ValueError(f"Missing description for {key}")
            self.descriptions[key] = description
        vectors = _normalize(model.encode(list(self.descriptions.values()))) if contractors else []
        self.embeddings = dict(zip(self.descriptions, vectors))
        # Cache belongs to this instance and is bounded.
        self._query = lru_cache(maxsize=256)(self._encode_query)

    def _encode_query(self, text):
        return _normalize(self.model.encode([text]))[0]

    def rank_and_explain(self, candidates: list[dict], req: FindRequest) -> list[dict]:
        if not req.event_format.strip():
            raise ValueError("event_format cannot be empty")
        if req.budget_kzt < 0 or (req.duration_hours is not None and req.duration_hours <= 0):
            raise ValueError("Invalid budget or duration")
        if not candidates:
            return []
        ids = [str(c["id"]) for c in candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate candidate ids")
        for c in candidates:
            if self.descriptions.get(str(c["id"])) != c["description"]:
                raise ValueError("Unknown or changed contractor; reinitialize ranking at startup")
        with self._lock:
            query = self._query(req.event_format)
        results = []
        for c in candidates:
            score = float(np.clip(np.dot(self.embeddings[str(c["id"])] , query), -1, 1))
            results.append({**c, "score": score, "explanation": explain(c, req)})
        return sorted(results, key=lambda c: (-c["score"], str(c["id"])))


def explain(c: dict, req: FindRequest) -> str:
    reasons = []
    price = c.get("price_from_kzt")
    if price is not None and price <= req.budget_kzt:
        price_note = "оценочная цена" if c.get("price_imputed") else "цена"
        reasons.append(f"{price_note} от {price:,} ₸ укладывается в бюджет {req.budget_kzt:,} ₸".replace(",", " "))
    if req.language and req.language in (c.get("languages") or []):
        reasons.append(f"язык работы: {req.language}")
    hours = c.get("max_hours")
    if req.duration_hours is not None and hours is not None and hours >= req.duration_hours:
        reasons.append(f"работает до {hours:g} ч — достаточно для запрошенных {req.duration_hours:g} ч")
    # Include the actual source evidence, even when price/language are identical.
    # Do not claim a format match merely because cosine similarity was calculated.
    description = " ".join(c["description"].split())
    evidence = f"В описании исполнителя: «{description}»"
    if reasons:
        facts = "; ".join(reasons)
        return facts[0].upper() + facts[1:] + ". " + evidence + "."
    return "Основание семантического сравнения — описание исполнителя: «" + description + "»."


_ranker: Ranker | None = None


def initialize_ranking(contractors: list[dict], model: Any = None) -> None:
    global _ranker
    _ranker = Ranker(contractors, model=model)


def rank_and_explain(candidates: list[dict], req: FindRequest) -> list[dict]:
    if _ranker is None:
        raise RuntimeError("Call initialize_ranking(dataset) during server startup first")
    return _ranker.rank_and_explain(candidates, req)

