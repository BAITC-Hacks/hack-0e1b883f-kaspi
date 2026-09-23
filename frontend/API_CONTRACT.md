# Backend API contract

The frontend sends `POST http://127.0.0.1:8001/api/find` with `Content-Type: application/json`. Required fields are `city`, `event_date` (`YYYY-MM-DD`), `event_format`, `category`, and integer `budget_kzt`. Optional `duration_hours` and `language` are omitted when blank. The frontend's date picker allows 2026-09-23 through 2026-12-31.

The backend returns `status` (`ok`, `no_category_in_city`, or `no_match`), `candidates`, `excluded_count`, and `excluded_reasons`. Each candidate has `id`, `name`, `category`, `city`, `price_from_kzt`, `explanation`, `synthetic`, `price_imputed`, and `city_imputed`. The backend may return more than three candidates; the frontend displays all of them in order. Starting prices are per event, and imputed prices are labelled estimates.

The frontend validates the response before display and shows a technical error for invalid responses. Missing explanatory text is shown as a contract warning. Backend text is inserted with `textContent`.
