# Contractor Finder API

From `backend/` (Python 3.10+ recommended; tested on 3.9):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/docs → POST `/api/find` → Try it out:

```json
{
  "city": "Алматы",
  "event_date": "2026-11-14",
  "event_format": "корпоратив",
  "category": "Ведущий",
  "budget_kzt": 1000000,
  "duration_hours": 4,
  "language": "русский"
}
```

The supplied anonymized hackathon dataset is stored unchanged in
`data/contractors.csv`: 66 rows, including 13 marked synthetic by the source.
The response preserves synthetic, price_imputed and city_imputed flags.
Imputed prices are described as estimates. Prices are starting prices, not final
quotes. The default example returns the top three of five eligible candidates
and excludes five for failing the filters.

Set `CONTRACTORS_PATH=/absolute/path/dataset.csv` to use a replacement with the
same columns. Pipe-delimited categories, event_formats, languages and busy_dates
are parsed into lists. CSV booleans are parsed explicitly, not by string truthiness.
Blank max_hours becomes null. Original CSV bytes are preserved.

`busy_dates` contains unavailable dates: a contractor is excluded when the
requested date is listed. Absence is treated as not booked under this dataset's
calendar convention, not a live booking guarantee. Unknown max_hours fails an
explicit duration requirement. Multiple categories are supported. City/category
comparisons ignore case; language accepts Russian names and RU/KZ/KK/EN aliases.
Event format is used for semantic ranking, not an exact-match exclusion.
Excluded counts cover the selected city/category only; multiple exclusion reasons
can apply to one row.

Startup validates the dataset and computes embeddings once per server process.
The first startup downloads the model; wait for application startup complete.
`/health` reports loaded row and synthetic counts. Failure to load data/model
stops startup. Restart after dataset changes. Query embeddings are cached.

`/api/find` performs filters → ranking → factual explanations and returns
`ok`, `no_category_in_city` or `no_match`. Ties use string ID order. LLM calls are
not used. The existing response fields are preserved; data provenance flags are
added. Explanation text must be displayed as text, not unescaped HTML.

Canonical code is in `app/`; tests in `tests/`. `requirments.txt` forwards to
`requirements.txt` for compatibility with the initial repository. Exact tested
package versions are recorded in `requirements.lock.txt`.

The frontend in `../frontend` sends requests to this API at port 8001. Swagger
`/docs` also provides an API testing form. Unit/API tests use a fake encoder;
separate verification uses the actual model.
