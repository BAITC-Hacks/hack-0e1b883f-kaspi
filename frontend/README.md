# Smart Contractor Matching — Phase 1 frontend

One Russian-language page with event requirements, validation and up to three response cards. Plain HTML, CSS and JavaScript modules; no framework, build system, runtime dependencies or external assets. Phase 1 is mock-only. No backend files, shared configuration or original data files are changed.

## Run over HTTP

From the repository root:

```sh
cd frontend
python3 -m http.server 8000 --bind 127.0.0.1
```

Open **http://127.0.0.1:8000/?mock=1**. If your terminal is already in `frontend`, run only the Python command. Stop with Ctrl+C. Do not open `index.html` using `file://`: JavaScript modules require HTTP.

Mock mode requires the explicit `?mock=1` parameter. The page displays `Тестовые данные — бэкенд не подключён`. Without it, development controls are hidden and data access reports that the backend is not connected. There is no live API adapter and no automatic fallback to mock data.

## Demonstration

The development-only controls below the form select a fixed response. Choose a scenario, click `Заполнить пример`, then `Подобрать подрядчиков`. Scenario selection alone does not change form values or an already displayed result. Editing parameters does not change fixed fixture results. The submitted parameter snapshot and submitted scenario label stay attached to their results.

Available scenarios: three cards, two cards, one florist card, category absent in city, no match, technical failure, invalid response, missing reasons, missing explanation. Initial and loading states appear before and during searches; the 600 ms mock delay makes loading inspectable. Submission and scenario controls are disabled during loading; form inputs remain editable.

Explanations and exclusion reasons are explicitly authored **test content**, not live backend or AI output. They describe source profile facts but the response sets, counts and exclusion reasons are controlled demonstrations, not computed catalog results. The one-card scenario demonstrates an existing synthetic florist profile with `max_hours=null`: duration does not apply, rather than meaning unavailable or zero hours.

## Files and boundaries

- `index.html`, `styles.css`: accessible form and responsive page.
- `src/app.js`: DOM rendering and UI states; all external text is assigned with `textContent`.
- `src/domain.js`: input validation and draft response checks; no eligibility or ranking.
- `src/api.js`: the sole data-access entry point, `findContractors(params)`; currently only fixed mock responses.
- `src/fixtures.js`: fixed test scenarios and example input values.
- `API_CONTRACT.md`: draft schema, recoverable missing-content behavior and integration questions.
- `tests/domain.test.mjs`, `tests/browser.test.mjs`: contract/validation and browser interaction checks.
- `.gitignore`: local QA screenshots under `test-results/` are excluded.

No original dataset is loaded at runtime. The frontend never scrapes the preview, matches, ranks, checks availability, replaces candidates, calls an LLM, or stores secrets. Real API integration belongs to a later phase after contract confirmation.

## Source inspection and fixture provenance

The repository initially contained a root README and an empty frontend directory. There were no applicable `AGENTS.md` files or confirmed API schema. All three supplied files were available under the user's Downloads directory:

- `hackathon dataset anonymized .csv`: 66 profiles, parsed read-only with Python `csv.DictReader`; pipe-delimited lists, explicit `True`/`False` booleans, blank `max_hours` as null. SHA-256: `6a724b6b7dfb5973343e68ba18dadb60fc807d87e3d78f03ee86fb26cb089f7d`.
- `hackathon dataset preview.html`: inspected as a partial preview, never as the complete calendar. SHA-256: `d9952a6dda0f2acacd4407ee6ac77488fe0c604d14b5a2207933cccb81e0468f`.
- `HackAlem AI_ Хакатон-задача_ умный подбор подрядчиков (2).docx`: challenge brief read as reference material. The user's Phase 1 scope takes precedence over its full-product requirements. SHA-256: `f38c82705897a36d3d9b83ae0401ecc02b9aaaf9b60786ed8e72d829291a7fe9`.

| Source ID | Display name from `anon_name` | Category | City | Starting KZT | Source synthetic |
| --- | --- | --- | --- | ---: | --- |
| HK-30583 | Леорио Паради | Фотограф | Алматы | 350000 | false |
| HK-76268 | Сацуки Кусакабэ | Фотограф | Алматы | 200000 | false |
| HK-91112 | Мэгуми Фушигуро | Фотограф | Алматы | 300000 | false |
| HK-90001 | Тихиро Огино | Флорист | Алматы | 250000 | true |

The original catalog already contains 13 synthetic profiles. The team did not create these source profiles. Explanations use these profiles' listed formats, languages, duration limits and descriptions; fixture cards intentionally need no optional imputation fields. Prices are per-event starting amounts, not final quotes. The deliberately non-price-sorted three-card order makes it easy to verify that rendering preserves response order.

## Checks

Use Node.js 22 or newer for the standalone ES-module tests. Node is only needed for tests, not to serve the page:

```sh
node --test tests/domain.test.mjs
```

Browser checks need Playwright available to Node and an installed Chromium browser. With the HTTP server running:

```sh
node tests/browser.test.mjs
```

Optional environment variables: `BASE_URL` (default `http://127.0.0.1:8000`), `BROWSER_EXECUTABLE_PATH` (an existing Chrome/Chromium executable), and `NODE_PATH` (an existing directory containing Playwright). This repository deliberately has no npm install/build step. Screenshots are saved to ignored `test-results/` for visual review.

The checks cover required fields, date boundaries and impossible dates, finite positive numbers, omission of blank optionals, exact catalog values, invalid/inconsistent response shapes, unchanged response order, and missing-content warnings. Browser coverage additionally exercises all scenarios, loading duplicate prevention, immutable submitted summaries, form retention, retry, synthetic labels, hostile text rendering, mobile overflow, mock gating and absence of API/external requests. See `CHECKS.md` for executed results.

## Manual browser checklist

1. Open `?mock=1`; confirm the test banner and initial state. Submit an empty form and review the Russian field errors and focused field.
2. Select each mock scenario, fill its example and submit. Verify the exact response order, complete explanations, count/reasons and synthetic badge.
3. Try zero/negative budgets and durations, blank optional duration, and dates before/after the allowed range. Try both date endpoints.
4. During loading, try a second submit and edit a form value. Confirm there is one search and the results retain the originally submitted parameters.
5. Trigger request failure and invalid response. Check that these are visibly technical errors, values remain, and retry works after selecting another scenario.
6. Check missing reasons/explanations: neutral notices plus contract warnings, with no fabricated text.
7. Use keyboard navigation and a narrow mobile viewport. Confirm readable explanations, visible focus, associated labels/errors and no horizontal scrolling.
8. Open without `?mock=1`: no development controls, no fake results and no `/api/find` requests.
