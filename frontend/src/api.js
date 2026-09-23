// The frontend and API use separate ports during local development.
export const API_BASE_URL = "http://127.0.0.1:8001";

export async function findContractors(params) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/find`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
  } catch {
    throw new Error("Не удалось связаться с сервером. Проверьте, что бэкенд запущен, и повторите поиск.");
  }
  if (!response.ok) throw new Error(`Сервер вернул ошибку ${response.status}. Проверьте параметры и повторите поиск.`);
  try {
    return await response.json();
  } catch {
    throw new Error("Сервер вернул ответ, который не удалось прочитать.");
  }
}
