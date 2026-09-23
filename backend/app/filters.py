"""Dataset busy dates exclude contractors; unknown duration cannot satisfy a request."""
from collections import Counter
from app.models import FindRequest


def filter_candidates(contractors: list[dict], req: FindRequest):
    scoped = [c for c in contractors if c["city"].casefold() == req.city.casefold()
              and req.category.casefold() in [v.casefold() for v in c["categories"]]]
    if not scoped:
        return [], "no_category_in_city", 0, []
    matched, reasons = [], Counter()
    for c in scoped:
        failed = []
        if req.event_date.isoformat() in c["busy_dates"]:
            failed.append("Занят на выбранную дату")
        if c["price_from_kzt"] > req.budget_kzt:
            failed.append("Цена выше бюджета")
        if req.language and req.language not in c["languages"]:
            failed.append("Не указан запрошенный язык")
        if req.duration_hours is not None and (c["max_hours"] is None or c["max_hours"] < req.duration_hours):
            failed.append("Не подтверждена нужная длительность")
        if failed:
            reasons.update(failed)
        else:
            matched.append(c)
    return matched, "ok" if matched else "no_match", len(scoped) - len(matched), [
        f"{reason}: {count}" for reason, count in sorted(reasons.items())]
