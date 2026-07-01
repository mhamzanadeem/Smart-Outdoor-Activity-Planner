import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

/**
 * Send a chat message to the SkyWise agent.
 * @param {string} message
 * @param {string|null} sessionId
 * @returns {Promise<import("./types").ChatResponse>}
 */
export async function sendMessage(message, sessionId = null) {
  const payload = { message };
  if (sessionId) payload.session_id = sessionId;
  const { data } = await apiClient.post("/chat", payload);
  return data;
}

/**
 * Quick health probe used for UI availability checks.
 */
export async function checkServerHealth() {
  const { data } = await apiClient.get("/health", { timeout: 4000 });
  return data;
}

/**
 * Wake call for free-tier backends that spin down.
 * Uses a longer timeout because cold starts can take ~50s.
 */
export async function wakeServer() {
  const { data } = await apiClient.get("/health", { timeout: 70000 });
  return data;
}

export default apiClient;
