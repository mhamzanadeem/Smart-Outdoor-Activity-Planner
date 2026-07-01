import { useState, useRef, useEffect, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import { checkServerHealth, sendMessage, wakeServer } from "./api";
import Header from "./components/Header";
import ChatMessage from "./components/ChatMessage";
import TypingIndicator from "./components/TypingIndicator";
import SuggestionPills from "./components/SuggestionPills";
import ChatInput from "./components/ChatInput";
import ErrorBanner from "./components/ErrorBanner";
import { CloudSun, Power, RefreshCcw } from "lucide-react";

const SESSION_KEY = "skywise_session_id";

function getOrCreateSessionId() {
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = uuidv4();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [serverStatus, setServerStatus] = useState("checking");
  const [serverMessage, setServerMessage] = useState("Checking backend status...");
  const [sessionId] = useState(getOrCreateSessionId);
  const bottomRef = useRef(null);

  const isServerActive = serverStatus === "active";

  // Auto-scroll to bottom on new messages / loading state change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const probeServer = useCallback(async () => {
    try {
      await checkServerHealth();
      setServerStatus("active");
      setServerMessage("");
    } catch {
      setServerStatus("inactive");
      setServerMessage(
        "Backend server is inactive (free tier sleep). Click Wake Server to activate it."
      );
    }
  }, []);

  useEffect(() => {
    probeServer();
  }, [probeServer]);

  const handleWakeServer = useCallback(async () => {
    setServerStatus("waking");
    setServerMessage("Waking backend server. This can take up to 50-60 seconds...");
    try {
      await wakeServer();
      setServerStatus("active");
      setServerMessage("");
      setError(null);
    } catch {
      setServerStatus("inactive");
      setServerMessage("Server is still sleeping. Please click Wake Server again in a few seconds.");
    }
  }, []);

  const handleSend = useCallback(
    async (overrideText) => {
      const text = (overrideText ?? inputValue).trim();
      if (!text || isLoading || !isServerActive) return;

      setError(null);
      setInputValue("");
      setMessages((prev) => [
        ...prev,
        { id: uuidv4(), role: "user", content: text },
      ]);
      setIsLoading(true);

      try {
        const data = await sendMessage(text, sessionId);

        // If the backend returned a typed error (API key problem, etc.),
        // show it as an inline error bubble instead of a raw answer
        if (data.error_code && data.error_message) {
          setMessages((prev) => [
            ...prev,
            {
              id: uuidv4(),
              role: "error",
              content: data.error_message,
              metadata: { error_code: data.error_code },
            },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              id: uuidv4(),
              role: "agent",
              content: data.final_answer,
              metadata: {
                tool_called: data.tool_called,
                tool_executions: data.tool_executions,
                reasoning: data.reasoning,
                weather_data: data.weather_data,
                weather_data_list: data.weather_data_list,
                intent: data.intent,
                city: data.city,
              },
            },
          ]);
        }
      } catch (err) {
        // Network / HTTP errors → floating banner
        const status = err?.response?.status;
        let detail;
        if (!navigator.onLine || err?.code === "ERR_NETWORK") {
          detail = "🔌 Cannot reach the server. Is the backend running on port 8000?";
          setServerStatus("inactive");
          setServerMessage(
            "Backend server appears inactive. Click Wake Server to activate it before chatting."
          );
        } else if (status === 422) {
          detail = "❌ Invalid request sent to the server.";
        } else if (status >= 500) {
          detail = "💥 Server error. Check the backend terminal for details.";
        } else {
          detail =
            err?.response?.data?.detail ||
            err?.message ||
            "Something went wrong. Please try again.";
        }
        setError(detail);
      } finally {
        setIsLoading(false);
      }
    },
    [inputValue, isLoading, isServerActive, sessionId]
  );

  function handleClear() {
    setMessages([]);
    setError(null);
    sessionStorage.removeItem(SESSION_KEY);
    window.location.reload();
  }

  const isEmpty = messages.length === 0 && !isLoading;

  return (
    <div className="flex flex-col h-screen max-h-screen overflow-hidden bg-gray-950">
      <Header onClear={handleClear} serverStatus={serverStatus} />

      {/* Messages area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">
          {!isServerActive && (
            <div className="flex flex-col gap-3 px-4 py-4 rounded-xl border border-amber-800/60 bg-amber-950/40 text-amber-200 animate-fade-in">
              <div className="flex items-start gap-3">
                <Power className="w-4 h-4 mt-0.5 text-amber-300" />
                <p className="text-sm leading-relaxed">
                  {serverMessage || "Backend server is inactive. Please wake it before chatting."}
                </p>
              </div>
              <div>
                <button
                  onClick={handleWakeServer}
                  disabled={serverStatus === "waking" || serverStatus === "checking"}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-amber-500 hover:bg-amber-400 text-gray-950 disabled:bg-amber-900/60 disabled:text-amber-200 disabled:cursor-not-allowed transition-colors"
                >
                  <RefreshCcw className={`w-4 h-4 ${serverStatus === "waking" ? "animate-spin" : ""}`} />
                  {serverStatus === "waking" ? "Waking..." : "Wake Server"}
                </button>
              </div>
            </div>
          )}

          {/* Empty / welcome state */}
          {isEmpty && (
            <div className="flex flex-col items-center justify-center py-12 gap-6 animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-brand-800/50 border border-brand-700/50 flex items-center justify-center shadow-xl shadow-brand-900/30">
                <CloudSun className="w-8 h-8 text-brand-300" />
              </div>
              <div className="text-center space-y-1.5">
                <h2 className="text-xl font-semibold text-white">
                  Hello, I'm SkyWise
                </h2>
                <p className="text-sm text-gray-400 max-w-xs leading-relaxed">
                  Your AI-powered weather &amp; outdoor activity planner. I use
                  live weather data to give you smart, personalised advice.
                </p>
              </div>
              <SuggestionPills onSelect={(s) => handleSend(s)} />
            </div>
          )}

          {/* Message history */}
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Typing / loading indicator */}
          {isLoading && <TypingIndicator />}

          {/* Error banner */}
          {error && (
            <ErrorBanner error={error} onDismiss={() => setError(null)} />
          )}

          {/* Quick-reply suggestions after first exchange */}
          {!isEmpty && !isLoading && messages.length > 0 && messages.length <= 4 && (
            <div className="pt-2">
              <p className="text-xs text-gray-600 text-center mb-2">
                Try asking…
              </p>
              <SuggestionPills onSelect={(s) => handleSend(s)} />
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={bottomRef} />
        </div>
      </main>

      {/* Sticky chat input */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={() => handleSend()}
        disabled={isLoading || !isServerActive}
      />
    </div>
  );
}
