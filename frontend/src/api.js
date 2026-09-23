import { getFixture } from "./fixtures.js";

export const MOCK_MODE = new URLSearchParams(globalThis.location?.search ?? "").get("mock") === "1";
let scenario = "three";

export function setMockScenario(key) {
  if (!MOCK_MODE) throw new Error("Mock mode must be explicitly enabled");
  getFixture(key);
  scenario = key;
}

// The single data-access boundary. Phase 1 intentionally contains no fetch or live adapter.
// params is the validated draft request; fixtures deliberately do not match against it.
export async function findContractors(params) {
  if (!MOCK_MODE) throw new Error("Подключение к серверу ещё не настроено. Откройте тестовый режим по ссылке вверху страницы.");
  if (!params || typeof params !== "object") throw new TypeError("Expected search parameters");
  const fixture = getFixture(scenario);
  await new Promise((resolve) => setTimeout(resolve, 600));
  if (fixture.error) throw new Error("Тестовая ошибка соединения. Выберите другой сценарий и повторите поиск.");
  return fixture.response;
}
