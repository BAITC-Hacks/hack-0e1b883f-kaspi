# Contractor Finder frontend

Plain HTML, CSS, and JavaScript. The form sends a JSON `POST` to the backend's `/api/find` endpoint. The response is rendered in backend order, including all eligible candidates, explanations, exclusion reasons, and an estimated price label where applicable. There is no mock mode or local dataset.

## Run locally

In one terminal, from the repository root:

```sh
cd backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Backend startup loads the dataset and ranking model. The first run may download the model; wait for `Application startup complete`.

In another terminal:

```sh
cd frontend
python3 -m http.server 8000 --bind 127.0.0.1
```

Open http://127.0.0.1:8000/. The frontend API URL is set in `src/api.js` to `http://127.0.0.1:8001`. Use the same host in the browser; if the API runs elsewhere, change `API_BASE_URL`. The backend permits cross origin requests. Open http://127.0.0.1:8001/health to check backend readiness.

## Checks

```sh
cd frontend
node --test tests/domain.test.mjs
```

The browser test needs Playwright and Chromium. With the frontend server running, use `node tests/browser.test.mjs`. It intercepts the API request to verify browser behavior without requiring the ranking model.
