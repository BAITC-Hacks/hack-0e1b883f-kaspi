import test from "node:test";
import assert from "node:assert/strict";
import { validateSearch, inspectResponse, InvalidResponseError, CATEGORIES, formatDate } from "../src/domain.js";
import { getFixture } from "../src/fixtures.js";

const valid = { city: "Алматы", event_date: "2026-10-12", event_format: "свадьба", category: "Фотограф", budget_kzt: "350000", duration_hours: "", language: "" };

test("required values, complete catalog, and exact Russian request values", () => {
  assert.deepEqual(Object.keys(validateSearch({}).errors).sort(), ["budget_kzt", "category", "city", "event_date", "event_format"]);
  assert.equal(CATEGORIES.length, 17);
  for (const city of ["Алматы", "Астана", "Зарубежье"]) {
    for (const category of CATEGORIES) assert.deepEqual(validateSearch({ ...valid, city, category }).errors, {});
  }
  assert.equal(validateSearch(valid).params.event_format, "свадьба");
  assert.ok(validateSearch({ ...valid, city: "Almaty" }).errors.city);
  assert.ok(validateSearch({ ...valid, language: "English" }).errors.language);
});

test("date boundaries and calendar validity without timezone conversions", () => {
  for (const date of ["2026-09-23", "2026-12-31"]) {
    const { params, errors } = validateSearch({ ...valid, event_date: date });
    assert.deepEqual(errors, {});
    assert.equal(params.event_date, date);
  }
  for (const date of ["2026-09-22", "2027-01-01", "2026-11-31", "2026-10-00", "2026-13-01", "2026-9-23", "garbage", ""]) {
    assert.ok(validateSearch({ ...valid, event_date: date }).errors.event_date, date);
  }
  assert.equal(formatDate("2026-10-12"), "12.10.2026");
});

test("numeric constraints and omitted optional fields", () => {
  const { params } = validateSearch(valid);
  assert.equal(params.budget_kzt, 350000);
  assert.equal(Object.hasOwn(params, "duration_hours"), false);
  assert.equal(Object.hasOwn(params, "language"), false);
  for (const key of ["budget_kzt", "duration_hours"]) {
    for (const value of ["0", "-1", "NaN", "Infinity", "1e999", "abc"]) assert.ok(validateSearch({ ...valid, [key]: value }).errors[key], `${key}: ${value}`);
    assert.equal(validateSearch({ ...valid, [key]: "0.5" }).params[key], .5);
  }
  assert.equal(Object.hasOwn(validateSearch({ ...valid, duration_hours: "  " }).params, "duration_hours"), false);
  assert.equal(validateSearch({ ...valid, language: "казахский" }).params.language, "казахский");
});

test("valid statuses preserve response identity and backend order", () => {
  for (const key of ["three", "two", "one", "no_category", "no_match"]) {
    const fixture = getFixture(key).response;
    const snapshot = structuredClone(fixture);
    const { response, warnings } = inspectResponse(fixture);
    assert.equal(response, fixture);
    assert.deepEqual(response, snapshot);
    assert.deepEqual(warnings, []);
  }
  assert.deepEqual(inspectResponse(getFixture("three").response).response.candidates.map(c => c.price_from_kzt), [350000, 200000, 300000]);
  const copy = getFixture("one");
  copy.response.candidates[0].synthetic = false;
  assert.equal(getFixture("one").response.candidates[0].synthetic, true);
});

test("malformed and inconsistent responses are technical errors", () => {
  const ok = getFixture("three").response;
  const bad = [null, [], "ok", {}, getFixture("invalid").response,
    { ...ok, candidates: [] }, { ...ok, candidates: [...ok.candidates, ok.candidates[0]] },
    { ...ok, status: "no_match" }, { ...ok, candidates: null },
    { ...ok, excluded_count: -1 }, { ...ok, excluded_count: "2" },
    { ...ok, excluded_reasons: "busy" }, { ...ok, excluded_reasons: [""] },
    { ...getFixture("no_match").response, excluded_count: 0 },
    { ...getFixture("no_category").response, excluded_count: 1 },
    { ...ok, candidates: [ok.candidates[0], ok.candidates[0]] },
  ];
  for (const [key, value] of [["name", ""], ["id", 3], ["city", null], ["category", []], ["synthetic", "False"], ["price_from_kzt", "350000"], ["price_from_kzt", Infinity], ["explanation", {}]]) {
    bad.push({ ...ok, candidates: [{ ...ok.candidates[0], [key]: value }] });
  }
  for (const response of bad) assert.throws(() => inspectResponse(response), InvalidResponseError);
});

test("missing explanations and reasons remain visible contract warnings", () => {
  for (const key of ["missing_reasons", "missing_explanation"]) assert.equal(inspectResponse(getFixture(key).response).warnings.length, 1);
  const response = getFixture("no_match").response;
  delete response.excluded_reasons;
  assert.equal(inspectResponse(response).warnings.length, 1);
  assert.equal(Object.hasOwn(response, "excluded_reasons"), false);
  const cardResponse = getFixture("one").response;
  delete cardResponse.candidates[0].explanation;
  assert.equal(inspectResponse(cardResponse).warnings.length, 1);
});

test("data access refuses live mode without making a network request", async () => {
  const { findContractors, MOCK_MODE } = await import("../src/api.js");
  assert.equal(MOCK_MODE, false);
  await assert.rejects(() => findContractors(validateSearch(valid).params), /не настроено/);
});
