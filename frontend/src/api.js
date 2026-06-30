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

export default apiClient;
