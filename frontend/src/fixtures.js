// Fixed draft responses, not a matching engine. Facts copied from the supplied CSV.
// All explanations and exclusion reasons below are authored test content, not AI output.
const leorio = {
  id: "HK-30583", name: "Леорио Паради", category: "Фотограф", city: "Алматы",
  price_from_kzt: 350000, synthetic: false,
  explanation: "В каталоге указаны свадебная съёмка, русский и английский языки, до 8 часов на площадке. Стартовая цена — 350 000 ₸; в описании отмечены эстетика, атмосфера и детали.",
};
const satsuki = {
  id: "HK-76268", name: "Сацуки Кусакабэ", category: "Фотограф", city: "Алматы",
  price_from_kzt: 200000, synthetic: false,
  explanation: "Снимает свадьбы и той на русском языке, может работать на площадке до 10 часов. Цена начинается от 200 000 ₸; в описании — живые кадры и настоящие улыбки.",
};
const megumi = {
  id: "HK-91112", name: "Мэгуми Фушигуро", category: "Фотограф", city: "Алматы",
  price_from_kzt: 300000, synthetic: false,
  explanation: "Свадебный фотограф с русским языком работы и длительностью съёмки до 10 часов. Стартовая цена — 300 000 ₸; описание подчёркивает ненавязчивую съёмку и внимание к эмоциям пары.",
};
const chihiro = {
  id: "HK-90001", name: "Тихиро Огино", category: "Флорист", city: "Алматы",
  price_from_kzt: 250000, synthetic: true,
  explanation: "Оформляет свадьбы, юбилеи и той, работает на русском и казахском языках; цена начинается от 250 000 ₸. Композиции подбираются под цветовую палитру мероприятия, а ограничение часов на площадке к этому профилю не применяется.",
};
const photoExample = {
  city: "Алматы", event_date: "2026-10-12", event_format: "свадьба", category: "Фотограф",
  budget_kzt: 350000, duration_hours: 6, language: "русский",
};

export const SCENARIOS = {
  three: {
    label: "Три карточки", example: photoExample,
    response: { status: "ok", candidates: [leorio, satsuki, megumi], excluded_count: 0, excluded_reasons: [] },
  },
  two: {
    label: "Две карточки", example: photoExample,
    response: { status: "ok", candidates: [leorio, satsuki], excluded_count: 1, excluded_reasons: ["Один профиль исключён: в этом тестовом сценарии дата занята."] },
  },
  one: {
    label: "Одна карточка · флорист", example: { ...photoExample, category: "Флорист", budget_kzt: 250000, duration_hours: "" },
    response: { status: "ok", candidates: [chihiro], excluded_count: 1, excluded_reasons: ["В этом тестовом сценарии у второго профиля в городе стартовая цена выше бюджета."] },
  },
  no_category: {
    label: "Категории нет в городе", example: { ...photoExample, city: "Зарубежье", category: "Флорист" },
    response: { status: "no_category_in_city", candidates: [], excluded_count: 0, excluded_reasons: [] },
  },
  no_match: {
    label: "Никто не подошёл", example: { ...photoExample, budget_kzt: 100000 },
    response: { status: "no_match", candidates: [], excluded_count: 8, excluded_reasons: ["В этом тестовом сценарии стартовые цены всех восьми фотографов в городе выше бюджета."] },
  },
  error: { label: "Техническая ошибка", example: photoExample, error: true },
  invalid: {
    label: "Некорректный ответ", example: photoExample,
    response: { status: "unexpected", candidates: [], excluded_count: 0, excluded_reasons: [] },
  },
  missing_reasons: {
    label: "Не переданы причины", example: photoExample,
    response: { status: "ok", candidates: [leorio, satsuki], excluded_count: 1, excluded_reasons: [] },
  },
  missing_explanation: {
    label: "Не передано объяснение", example: photoExample,
    response: { status: "ok", candidates: [{ ...leorio, explanation: "" }], excluded_count: 2, excluded_reasons: ["Два профиля исключены по условиям тестового сценария."] },
  },
};

export function getFixture(key) {
  if (!Object.hasOwn(SCENARIOS, key)) throw new Error("Unknown mock scenario");
  // Each call owns its copy; UI code cannot mutate subsequent responses.
  return structuredClone(SCENARIOS[key]);
}
