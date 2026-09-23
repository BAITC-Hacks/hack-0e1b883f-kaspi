// Run against the static HTTP server. Playwright is a test dependency, not an app dependency.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const base = process.env.BASE_URL || "http://127.0.0.1:8000";
const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_EXECUTABLE_PATH ? { executablePath: process.env.BROWSER_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 }, locale: "ru-RU" });
const errors = [];
const requests = [];
page.on("pageerror", error => errors.push(error.message));
page.on("request", request => requests.push(request.url()));
await mkdir("test-results", { recursive: true });
const visible = async selector => assert.equal(await page.locator(selector).isVisible(), true, selector);
const run = async (scenario, fill = true) => {
  await page.selectOption("#mock-scenario", scenario);
  if (fill) await page.click("#fill-example");
  await page.click("#submit-button");
  await page.waitForSelector('#results-panel[aria-busy="false"]');
};

try {
  await page.goto(`${base}/?mock=1`);
  await visible('#result-content [data-state="initial"]');
  await visible("#mode-notice");
  await page.screenshot({ path: "test-results/initial-desktop.png", fullPage: true });
  await page.click("#submit-button");
  assert.equal(await page.locator('[aria-invalid="true"]').count(), 5);
  assert.equal(await page.locator("#city").evaluate(e => e === document.activeElement), true);
  for (const city of ["Алматы", "Астана", "Зарубежье"]) {
    await page.selectOption("#city", city);
    assert.equal(await page.locator("#category option").count(), 18);
  }
  await page.click("#fill-example");
  await page.evaluate(() => {
    window.loadingRenders = 0;
    new MutationObserver(records => {
      for (const record of records) for (const node of record.addedNodes) if (node.dataset?.state === "loading") window.loadingRenders += 1;
    }).observe(document.getElementById("result-content"), { childList: true });
    document.getElementById("requirements").requestSubmit();
    document.getElementById("requirements").requestSubmit();
  });
  await visible('[data-state="loading"]');
  assert.equal(await page.locator("#submit-button").isDisabled(), true);
  await page.selectOption("#city", "Астана");
  await page.waitForSelector('#results-panel[aria-busy="false"]');
  assert.equal(await page.evaluate(() => window.loadingRenders), 1);
  assert.match(await page.locator("#submitted-search").innerText(), /Алматы/);
  assert.equal(await page.inputValue("#city"), "Астана");
  assert.deepEqual(await page.locator(".candidate-card").evaluateAll(cards => cards.map(c => c.dataset.candidateId)), ["HK-30583", "HK-76268", "HK-91112"]);
  await page.screenshot({ path: "test-results/three-desktop.png", fullPage: true });
  for (const [key, count] of [["two", 2], ["one", 1]]) {
    await run(key);
    assert.equal(await page.locator(".candidate-card").count(), count);
    await visible(".reason-panel");
  }
  await visible(".synthetic-badge");
  assert.equal(await page.inputValue("#duration_hours"), "");
  await run("no_category");
  assert.equal(await page.locator('[data-state="no_category_in_city"] h3').innerText(), "В городе Зарубежье подрядчиков категории Флорист нет в каталоге.");
  await run("no_match");
  assert.equal(await page.locator('[data-state="no_match"] h3').innerText(), "Подрядчики есть, но ни один не подошёл.");
  await visible(".reason-panel li");
  await run("error");
  await visible('[data-state="technical"]');
  assert.equal(await page.inputValue("#budget_kzt"), "350000");
  assert.equal(await page.locator('[data-state="no_match"]').count(), 0);
  await page.selectOption("#mock-scenario", "three");
  await page.getByRole("button", { name: "Повторить поиск" }).click();
  await page.waitForSelector(".candidate-card");
  await run("invalid");
  assert.match(await page.locator("#result-content").innerText(), /Получен некорректный ответ/);
  for (const key of ["missing_reasons", "missing_explanation"]) {
    await run(key);
    await visible(".contract-notice");
  }
  for (const [id, value] of [["budget_kzt", "0"], ["duration_hours", "-2"], ["event_date", "2027-01-01"]]) {
    await page.click("#fill-example");
    await page.fill(`#${id}`, value);
    await page.click("#submit-button");
    await visible(`#${id}-error`);
  }
  await page.click("#fill-example");
  await page.fill("#duration_hours", "");
  await page.selectOption("#language", "");
  await run("three", false);
  assert.match(await page.locator("#submitted-search").innerText(), /Не указана/);
  assert.match(await page.locator("#submitted-search").innerText(), /Не важно/);
  // Force a response containing hostile markup and long text to exercise safe rendering.
  await page.evaluate(async () => {
    const { SCENARIOS } = await import("/src/fixtures.js");
    const c = SCENARIOS.three.response.candidates[0];
    c.name = '<img src=x onerror="window.injected=true">';
    c.explanation = '<script>window.injected=true</script> ' + 'Подробное объяснение. '.repeat(30);
  });
  await run("three");
  assert.equal(await page.locator(".candidate-card img, .candidate-card script").count(), 0);
  assert.equal(await page.evaluate(() => window.injected), undefined);
  assert.match(await page.locator(".candidate-card h3").first().innerText(), /<img/);
  assert.ok((await page.locator(".explanation p").first().innerText()).length > 500);
  await page.reload();
  await run("three");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "test-results/three-mobile.png", fullPage: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, "mobile overflow");
  await page.setViewportSize({ width: 320, height: 740 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, "320px overflow");
  await page.goto(base);
  await visible("#disconnected-notice");
  assert.equal(await page.locator("#dev-panel").isVisible(), false);
  assert.equal(await page.locator("#mode-notice").isVisible(), false);
  await page.selectOption("#city", "Алматы");
  await page.fill("#event_date", "2026-09-23");
  await page.selectOption("#event_format", "свадьба");
  await page.selectOption("#category", "Фотограф");
  await page.fill("#budget_kzt", "1");
  await page.click("#submit-button");
  await visible('[data-state="technical"]');
  assert.equal(requests.some(url => url.includes("/api/")), false);
  assert.equal(requests.some(url => !url.startsWith(base)), false);
  assert.deepEqual(errors, []);
  console.log("PASS: nine mock scenarios, validation, loading lock, response order, submitted snapshot, retry, safe text, mobile layouts, explicit mock gating, zero API/external requests, zero page errors.");
} finally {
  await browser.close();
}
