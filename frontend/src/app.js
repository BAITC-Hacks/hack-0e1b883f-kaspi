import { CITIES, EVENT_FORMATS, CATEGORIES, LANGUAGES, validateSearch, inspectResponse, InvalidResponseError, formatDate, formatNumber } from "./domain.js";
import { findContractors } from "./api.js";

const $ = (id) => document.getElementById(id);
const form = $("requirements");
const content = $("result-content");
const fields = ["city", "event_date", "event_format", "category", "budget_kzt", "duration_hours", "language"];
let loading = false;

// All response text uses textContent. Never interpolate backend strings into markup.
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

for (const [id, values] of [["city", CITIES], ["event_format", EVENT_FORMATS], ["category", CATEGORIES], ["language", LANGUAGES]]) {
  for (const value of values) {
    const option = element("option", "", value);
    option.value = value;
    $(id).append(option);
  }
}

function state(title, description, kind = "initial") {
  const box = element("div", `empty-state ${kind === "technical" ? "technical-state" : ""}`);
  box.dataset.state = kind;
  const symbol = element("div", "state-symbol", kind === "technical" ? "!" : kind === "loading" ? "" : "↗");
  symbol.setAttribute("aria-hidden", "true");
  if (kind === "loading") symbol.append(element("span", "spinner"));
  box.append(symbol, element("h3", "", title), element("p", "", description));
  return box;
}

const initial = state("Подборка начинается с вашего события", "Укажите город, дату и пожелания. Здесь появятся варианты с объяснением для каждого подрядчика.");
const steps = element("ol", "initial-steps");
["Параметры", "Подрядчики", "Объяснения"].forEach((text, index) => {
  const item = element("li");
  item.append(element("span", "", String(index + 1)), document.createTextNode(text));
  steps.append(item);
});
initial.append(steps);
content.append(initial);

function showValidation(errors) {
  for (const key of fields) {
    const message = errors[key];
    $(key).setAttribute("aria-invalid", String(Boolean(message)));
    $(`${key}-error`).hidden = !message;
    $(`${key}-error`).textContent = message ?? "";
  }
  const count = Object.keys(errors).length;
  $("validation-summary").hidden = count === 0;
  $("validation-summary").textContent = count ? "Проверьте отмеченные поля. Поиск ещё не отправлен." : "";
}
form.addEventListener("input", (event) => {
  if (!fields.includes(event.target.name)) return;
  const { errors } = validateSearch(Object.fromEntries(new FormData(form)));
  if (!$("validation-summary").hidden) showValidation(errors);
});

function showSubmitted(params) {
  const summary = $("submitted-search");
  summary.replaceChildren(element("h3", "", "Параметры отправленного поиска"));
  const terms = element("dl", "search-terms");
  const entries = [
    ["Город", params.city], ["Дата", formatDate(params.event_date)],
    ["Формат", params.event_format], ["Категория", params.category],
    ["Бюджет", `${formatNumber(params.budget_kzt)} ₸`],
    ["Длительность", params.duration_hours === undefined ? "Не указана" : `${formatNumber(params.duration_hours)} ч`],
    ["Язык", params.language ?? "Не важно"],
  ];
  for (const [label, value] of entries) {
    const pair = element("div");
    pair.append(element("dt", "", `${label}:`), element("dd", "", value));
    terms.append(pair);
  }
  summary.append(terms);
  summary.hidden = false;
}

function renderCard(candidate, index) {
  const card = element("article", "candidate-card");
  card.dataset.candidateId = candidate.id;
  const top = element("div", "card-top");
  const number = element("span", "candidate-number", String(index + 1).padStart(2, "0"));
  number.setAttribute("aria-label", `Позиция ${index + 1}`);
  const identity = element("div");
  identity.append(element("h3", "", candidate.name), element("p", "candidate-meta", `${candidate.category} · ${candidate.city}`));
  if (candidate.synthetic) identity.append(element("span", "synthetic-badge", "Синтетический профиль из датасета"));
  top.append(number, identity, element("p", "price", `${candidate.price_imputed ? "Оценочная цена от" : "Цена от"} ${formatNumber(candidate.price_from_kzt)} ₸`));
  const explanation = element("div", "explanation");
  explanation.append(element("h4", "", "Почему в подборке"));
  explanation.append(element("p", "", candidate.explanation?.trim() ? candidate.explanation : "Объяснение не передано. Основание рекомендации уточнить нельзя."));
  card.append(top, explanation);
  return card;
}

function renderReasons(response) {
  const reasons = response.excluded_reasons;
  if (!reasons?.length) return;
  const panel = element("div", "reason-panel");
  panel.append(element("h3", "", `Исключено подрядчиков: ${response.excluded_count}`));
  const list = element("ul");
  for (const reason of reasons) list.append(element("li", "", reason));
  panel.append(list);
  content.append(panel);
}

function renderResponse(response, warnings, params) {
  content.replaceChildren();
  if (response.status === "ok") {
    $("result-count").textContent = `Найдено: ${response.candidates.length}`;
    const cards = element("div", "candidate-list");
    cards.dataset.state = "ok";
    response.candidates.forEach((candidate, index) => cards.append(renderCard(candidate, index)));
    content.append(cards, element("p", "price-note", "Указана стартовая цена за мероприятие. Итоговая стоимость может отличаться."));
    renderReasons(response);
  } else if (response.status === "no_category_in_city") {
    $("result-count").textContent = "Категории нет в каталоге";
    content.append(state(`В городе ${params.city} подрядчиков категории ${params.category} нет в каталоге.`, "Вы можете выбрать другой город или другую категорию.", "no_category_in_city"));
    renderReasons(response);
  } else if (response.status === "no_match") {
    $("result-count").textContent = "Найдено: 0";
    content.append(state("Подрядчики есть, но ни один не подошёл.", "Причины исключения помогают понять, какие условия можно изменить.", "no_match"));
    renderReasons(response);
  }
  if (warnings.length) {
    const notice = element("div", "reason-panel contract-notice");
    notice.setAttribute("role", "note");
    notice.append(element("h3", "", "Нарушение контракта: не хватает пояснений"));
    for (const warning of warnings) notice.append(element("p", "", warning));
    content.append(notice);
    console.warn("API contract warnings:", warnings);
  }
  $("live-status").textContent = `${$("result-count").textContent}.${warnings.length ? " В ответе не хватает пояснений." : ""}`;
}

function setLoading(value) {
  loading = value;
  $("submit-button").disabled = value;
  $("results-panel").setAttribute("aria-busy", String(value));
  $("submit-label").textContent = value ? "Подбираем…" : "Подобрать подрядчиков";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (loading) return;
  const raw = Object.fromEntries(new FormData(form));
  const { params, errors } = validateSearch(raw);
  // Browsers can expose malformed number input as an empty string; do not omit it.
  for (const key of ["budget_kzt", "duration_hours"]) {
    if ($(key).validity.badInput) errors[key] = "Введите корректное число больше нуля.";
  }
  showValidation(errors);
  if (Object.keys(errors).length) {
    $(Object.keys(errors)[0]).focus();
    return;
  }
  const submitted = Object.freeze({ ...params });
  setLoading(true);
  showSubmitted(submitted);
  $("result-count").textContent = "Подбираем…";
  content.replaceChildren(state("Готовим подборку", "Ожидаем ответ сервера.", "loading"));
  $("live-status").textContent = "Поиск начат.";
  try {
    const { response, warnings } = inspectResponse(await findContractors(submitted));
    renderResponse(response, warnings, submitted);
  } catch (error) {
    const invalid = error instanceof InvalidResponseError;
    const title = invalid ? "Получен некорректный ответ" : "Не удалось получить подборку";
    $("result-count").textContent = "Техническая ошибка";
    const box = state(title, invalid ? `${error.message} Результат нельзя показать. Это ошибка формата ответа.` : error.message, "technical");
    const retry = element("button", "secondary-button", "Повторить поиск");
    retry.type = "button";
    retry.addEventListener("click", () => form.requestSubmit());
    box.append(retry);
    content.replaceChildren(box);
    $("live-status").textContent = `${title}. Значения формы сохранены.`;
    if (invalid) console.warn("API contract error:", error.message);
  } finally {
    setLoading(false);
    if (document.activeElement === $("submit-button") || document.activeElement === document.body) $("results-heading").focus({ preventScroll: true });
  }
});
