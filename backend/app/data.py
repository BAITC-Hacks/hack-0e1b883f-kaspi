import csv
from pathlib import Path
from app.models import Contractor


def split_values(value):
    return [part.strip() for part in value.split("|") if part.strip()]


def parse_bool(value):
    if value not in ("True", "False"):
        raise ValueError(f"Invalid boolean: {value!r}")
    return value == "True"


def load_contractors(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    result = []
    for row in rows:
        item = Contractor(
            id=row["id"], name=row["anon_name"], city=row["city"],
            categories=split_values(row["categories"]), description=row["description"],
            price_from_kzt=int(row["price_from_kzt"]),
            languages=split_values(row["languages"]),
            max_hours=float(row["max_hours"]) if row["max_hours"] else None,
            busy_dates=split_values(row["busy_dates"]),
            event_formats=split_values(row["event_formats"]),
            synthetic=parse_bool(row["synthetic"]),
            price_imputed=parse_bool(row["price_imputed"]),
            city_imputed=parse_bool(row["city_imputed"]),
        )
        result.append(item.model_dump(mode="json"))
    return result
