export const CITIES = ["Алматы", "Астана", "Зарубежье"];
export const EVENT_FORMATS = ["свадьба", "той", "корпоратив", "конференция", "юбилей", "день рождения"];
export const LANGUAGES = ["русский", "казахский", "английский"];
export const CATEGORIES = [
  "Банкетный зал", "Ведущий", "Ведущий церемонии", "Видеограф", "Декоратор",
  "Загородная площадка", "Инструменталист", "Лайв-бэнд", "Национальный ансамбль",
  "Отель", "Подарки и сувениры", "Ресторан", "Танцевальный коллектив", "Флорист",
  "Фото и видеобудки", "Фотограф", "Шоу-программа",
];
export const DATE_MIN = "2026-09-23";
export const DATE_MAX = "2026-12-31";

function validDate(value) {
  if (!/^2026-\d{2}-\d{2}$/.test(value) || value < DATE_MIN || value > DATE_MAX) return false;
  const [, month, day] = value.split("-").map(Number);
  const days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1];
}

// Form values are strings. Blank optional fields are deliberately omitted.
export function validateSearch(raw) {
  const errors = {};
  const params = {};
  for (const [key, values, message] of [
    ["city", CITIES, "Выберите город из списка."],
    ["event_format", EVENT_FORMATS, "Выберите формат мероприятия."],
    ["category", CATEGORIES, "Выберите категорию подрядчика."],
  ]) {
    if (!values.includes(raw[key])) errors[key] = message;
    else params[key] = raw[key];
  }
  if (!validDate(raw.event_date ?? "")) errors.event_date = "Укажите дату с 23.09.2026 по 31.12.2026 включительно.";
  else params.event_date = raw.event_date;
  for (const [key, label, required] of [
    ["budget_kzt", "Бюджет", true], ["duration_hours", "Длительность", false],
  ]) {
    const text = String(raw[key] ?? "").trim();
    if (!text && !required) continue;
    const number = Number(text);
    if (!text || !Number.isFinite(number) || number <= 0) errors[key] = `${label}: введите число больше нуля.`;
    else params[key] = number;
  }
  if (raw.language) {
    if (!LANGUAGES.includes(raw.language)) errors.language = "Выберите язык из списка или «Не важно».";
    else params.language = raw.language;
  }
  return { params, errors };
}

export class InvalidResponseError extends Error {
  constructor(detail) {
    super(detail);
    this.name = "InvalidResponseError";
  }
}

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const hasText = (value) => typeof value === "string" && value.trim().length > 0;

// Validate the draft contract without selecting, sorting, coercing or repairing data.
// Missing explanatory text is a visible contract warning, never fabricated content.
export function inspectResponse(response) {
  const reject = (detail) => { throw new InvalidResponseError(detail); };
  if (!isObject(response)) reject("Ответ должен быть объектом.");
  if (!["ok", "no_category_in_city", "no_match"].includes(response.status)) reject("Неизвестный статус ответа.");
  if (!Array.isArray(response.candidates)) reject("В ответе отсутствует список карточек.");
  if (!Number.isInteger(response.excluded_count) || response.excluded_count < 0) reject("Некорректное количество исключённых подрядчиков.");
  if (response.status === "ok" && (response.candidates.length < 1 || response.candidates.length > 3)) reject("Успешный ответ должен содержать от одной до трёх карточек.");
  if (response.status !== "ok" && response.candidates.length !== 0) reject("Карточки противоречат статусу пустого результата.");
  if (response.status === "no_category_in_city" && response.excluded_count !== 0) reject("Отсутствующая категория не может содержать исключённых подрядчиков.");
  if (response.status === "no_match" && response.excluded_count === 0) reject("Ответ сообщает о неподходящих подрядчиках, но их количество равно нулю.");
  const warnings = [];
  if (response.excluded_reasons !== undefined && (!Array.isArray(response.excluded_reasons) || !response.excluded_reasons.every(hasText))) reject("Причины исключения должны быть списком непустых строк.");
  const needsReasons = response.status === "no_match" || (response.status === "ok" && response.candidates.length < 3);
  if (response.excluded_reasons === undefined || (needsReasons && response.excluded_reasons.length === 0)) {
    warnings.push("Причины не переданы. Причину сокращённой или пустой подборки уточнить нельзя.");
  }
  const ids = new Set();
  response.candidates.forEach((candidate, index) => {
    if (!isObject(candidate)) reject(`Карточка ${index + 1} должна быть объектом.`);
    for (const key of ["id", "name", "category", "city"]) {
      if (!hasText(candidate[key])) reject(`В карточке ${index + 1} отсутствует обязательное текстовое поле «${key}».`);
    }
    if (ids.has(candidate.id)) reject("В ответе повторяется идентификатор подрядчика.");
    ids.add(candidate.id);
    if (typeof candidate.price_from_kzt !== "number" || !Number.isFinite(candidate.price_from_kzt) || candidate.price_from_kzt < 0) reject(`Некорректная цена в карточке ${index + 1}.`);
    if (typeof candidate.synthetic !== "boolean") reject(`Некорректный признак синтетического профиля в карточке ${index + 1}.`);
    if (candidate.explanation !== undefined && typeof candidate.explanation !== "string") reject(`Некорректный формат объяснения в карточке ${index + 1}.`);
    if (!hasText(candidate.explanation)) warnings.push(`Карточка ${index + 1}: объяснение не передано.`);
  });
  return { response, warnings };
}

export function formatDate(value) {
  return value.split("-").reverse().join(".");
}
export const formatNumber = (value) => new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 20 }).format(value);
