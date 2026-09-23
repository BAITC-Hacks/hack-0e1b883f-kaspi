# DRAFT API contract — mock development only

No confirmed API contract, backend schema, or backend implementation was present in this checkout when Phase 1 was implemented. This proposal is not evidence that a backend supports it. No HTTP API requests are implemented in Phase 1.

## Proposed request

`POST /api/find`, `Content-Type: application/json`

```json
{
  "city": "Алматы",
  "event_date": "2026-10-12",
  "event_format": "свадьба",
  "category": "Фотограф",
  "budget_kzt": 350000,
  "duration_hours": 6,
  "language": "русский"
}
```

Required: `city`, `event_date`, `event_format`, `category`, `budget_kzt`. Optional fields are **omitted** when blank, pending confirmation; they are never converted to zero. Budget and supplied duration must be finite numbers greater than zero. Fractional positive values are accepted in this draft. Dates are calendar strings `YYYY-MM-DD` in the inclusive range `2026-09-23` through `2026-12-31`, without timezone conversion. All catalog values remain in Russian exactly as supplied; allowed lists are in `src/domain.js`. Every city offers the complete category list.

## Proposed response

```json
{
  "status": "ok",
  "candidates": [
    {
      "id": "HK-30583",
      "name": "Леорио Паради",
      "category": "Фотограф",
      "city": "Алматы",
      "price_from_kzt": 350000,
      "explanation": "Illustrative test text only; the backend must supply a grounded Russian explanation.",
      "synthetic": false
    }
  ],
  "excluded_count": 2,
  "excluded_reasons": ["Illustrative test reason only; the backend must supply Russian reasons."]
}
```

| Field | Draft type and behavior |
| --- | --- |
| `status` | `ok`, `no_category_in_city`, or `no_match`; determines the UI state |
| `candidates` | Array; 1–3 cards for `ok`, empty for either empty-result status |
| `excluded_count` | Nonnegative integer; draft assumes zero for `no_category_in_city` and positive for `no_match` |
| `excluded_reasons` | Array of nonempty Russian strings; required, may be empty for three cards or missing category; fewer than three successful cards and `no_match` require reasons |
| `id` | Unique nonempty string within the response |
| `name`, `category`, `city` | Nonempty strings |
| `price_from_kzt` | Finite nonnegative number, starting price per event, never a final quote |
| `explanation` | Nonempty Russian string; grounded 1–2 sentences, fully displayed |
| `synthetic` | Boolean, not a string; true displays the synthetic badge |

The source has `anon_name` and pipe-delimited `categories`, not `name` and singular `category`. The backend must explicitly map `anon_name` to `name` and provide the agreed singular category for this request. The frontend does not guess this mapping from arbitrary response fields. Other fields such as `price_imputed` and `city_imputed` are not required or displayed by Phase 1.

The backend owns eligibility, full-calendar availability, deterministic ranking, explanations, exclusion accounting and status. The frontend preserves every returned candidate and the exact response order. It does not fill missing slots, sort by price, filter candidates, infer an empty status, or match against the CSV.

## Invalid responses and missing explanations

Unknown statuses, wrong types, duplicate IDs, more than three cards, `ok` with no cards, empty statuses with cards, and the count inconsistencies above produce a technical error. No coercion or shape guessing occurs.

Missing/blank explanatory text is the deliberate recoverable exception: otherwise valid cards/status remain visible with neutral missing-content notices and an explicit contract warning, also reported with `console.warn`. Missing `excluded_reasons` is not silently converted to an empty list. A wrong type, null, or blank list entry is a technical error. No explanation or exclusion reason is invented. The draft requires final backend text even though mock text is authored locally.

## Questions to confirm before Phase 2

1. Is this exact request/response envelope and these three statuses accepted?
2. Should blank optional fields be omitted or sent as `null`? Are fractional budgets/durations valid?
3. Will the backend provide `name` and the requested singular `category`, especially for multi-category profiles?
4. What population does `excluded_count` count? Are the proposed zero/positive constraints correct? Can a short result have zero exclusions because the catalog itself is small?
5. Will exclusion reasons always be Russian strings, including catalog scarcity when fewer than three cards are available? How are missing explanations represented and should they remain recoverable?
6. Which HTTP status codes/error envelope, deployment origin/base URL, CORS policy and timeout apply? Who performs retry? These are intentionally unimplemented.
7. Should supplied imputation flags be displayed, and can a zero starting price occur?

Replace the draft with the team's confirmed contract before implementing real transport. Never put a provider API key in the frontend.
