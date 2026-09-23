"""Initialize once at startup, then pass the filtered dataset to rank_and_explain."""
from __future__ import annotations

from functools import lru_cache
import re
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
        evidence = {}
        used = set()
        # Stable allocation also handles shared or identical marketing bios.
        for c in sorted(candidates, key=lambda c: str(c["id"])):
            options = description_evidence_options(c["description"], req.event_format)
            if not options:
                evidence[str(c["id"])] = ""
                continue
            detail = next((option for option in options if option not in used), None)
            if detail is None:
                detail = f"{options[0]} (профиль {c['id']})"
                while detail in used:
                    detail += " (другой профиль)"
            used.add(detail)
            evidence[str(c["id"])] = detail
        results = []
        used_explanations = set()
        for c in sorted(candidates, key=lambda c: str(c["id"])):
            score = float(np.clip(np.dot(self.embeddings[str(c["id"])] , query), -1, 1))
            explanation = explain(c, req, evidence=evidence[str(c["id"])])
            # If no description evidence exists, equal structured facts may tie.
            if explanation in used_explanations:
                explanation = f"{explanation.rstrip('.')} (профиль {c['id']})."
                while explanation in used_explanations:
                    explanation = explanation.rstrip('.') + " (другой профиль)."
            used_explanations.add(explanation)
            results.append({**c, "score": score,
                            "explanation": explanation})
        return sorted(results, key=lambda c: (-c["score"], str(c["id"])))


def bounded_excerpt(clause: str) -> str:
    """Treat length limits as targets; never cut through an unfinished clause."""
    limit = min(len(" ".join(clause.split()[:12])), 160)
    if len(clause) <= limit:
        return clause
    for boundary in reversed(list(re.finditer(r"[.!?—–]", clause[:limit + 1]))):
        excerpt = clause[:boundary.start()].rstrip()
        # A short lead-in such as "Totoro Golf Club –" is not a useful excerpt.
        if len(excerpt.split()) >= 5:
            return excerpt
    boundary = re.search(r"[.!?]", clause[limit:])
    if boundary:
        return clause[:limit + boundary.start()].rstrip()
    # Selection already splits at sentence endings, so the end of this fragment
    # is the next boundary even though its terminal punctuation was removed.
    return clause


def description_evidence_options(description: str, event_format: str) -> list[str]:
    """Report bounded lexical evidence, without endorsing claims from the bio."""
    stopwords = {"для", "или", "как", "это", "при", "без", "под", "над", "the", "and", "for"}
    description_words = set(re.findall(r"[^\W\d_]+", description.casefold()))
    query_words = dict.fromkeys(re.findall(r"[^\W\d_]+", event_format.casefold()))
    matches = [word for word in query_words
               if 3 <= len(word) <= 30 and word not in stopwords and word in description_words][:3]
    if matches:
        return [f"В описании найдены ключевые слова запроса: «{', '.join(matches)}»"]
    # Extract a detail, not a claim that this clause caused the embedding score.
    # Leave price, language and hours claims to the structured fields.
    clauses = [" ".join(clause.split()).strip(" —:•«»")
               for clause in re.split(r"[.!?;\n]+", description)]
    clauses = [clause for clause in clauses if clause and not re.search(
        r"\b(?:\w*язы[кч]\w*|русск\w*|казахск\w*|английск\w*|"
        r"цен(?:а|ы|у|е|ой)|стоим\w*|тенге|час(?:а|ов|ы|у|ом)?|ч)\b|₸", clause, re.I)]
    clauses.sort(key=lambda clause: not bool(re.search(
        r"стиль|подач|юмор|специал|опыт|квиз|жив\w* музык", clause, re.I)))
    options = []
    for clause in clauses:
        excerpt = bounded_excerpt(clause)
        option = f"В описании отмечено: «{excerpt}»"
        if option not in options:
            options.append(option)
    return options


def description_relevance(description: str, event_format: str) -> str:
    options = description_evidence_options(description, event_format)
    return options[0] if options else ""


def explain(c: dict, req: FindRequest, *, evidence: str | None = None) -> str:
    reasons = []
    price = c.get("price_from_kzt")
    if price is not None and price <= req.budget_kzt:
        price_note = "оценочная цена" if c.get("price_imputed") else "цена"
        reasons.append(f"{price_note} от {price:,} ₸ укладывается в бюджет {req.budget_kzt:,} ₸".replace(",", " "))
    languages = c.get("languages") or []
    if req.language and req.language in languages:
        reasons.append(f"язык работы: {req.language}")
    elif req.language is None and languages:
        reasons.append(f"языки работы: {', '.join(languages)}")
    if req.event_format.casefold() in [value.casefold() for value in c.get("event_formats", [])]:
        reasons.append(f"формат «{req.event_format}» указан в профиле")
    hours = c.get("max_hours")
    if req.duration_hours is not None and hours is not None and hours >= req.duration_hours:
        reasons.append(f"работает до {hours:g} ч — достаточно для запрошенных {req.duration_hours:g} ч")
    if evidence is None:
        evidence = description_relevance(c["description"], req.event_format)
    if reasons:
        facts = "; ".join(reasons)
        text = facts[0].upper() + facts[1:] + "."
        return text + " " + evidence + "." if evidence else text
    return evidence + "." if evidence else f"Профиль исполнителя {c['id']}."


_ranker: Ranker | None = None


def initialize_ranking(contractors: list[dict], model: Any = None) -> None:
    global _ranker
    _ranker = Ranker(contractors, model=model)


def rank_and_explain(candidates: list[dict], req: FindRequest) -> list[dict]:
    if _ranker is None:
        raise RuntimeError("Call initialize_ranking(dataset) during server startup first")
    return _ranker.rank_and_explain(candidates, req)
