import { useState, useRef, useEffect, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import { sendMessage } from "./api";
import Header from "./components/Header";
import ChatMessage from "./components/ChatMessage";
import TypingIndicator from "./components/TypingIndicator";
import SuggestionPills from "./components/SuggestionPills";
import ChatInput from "./components/ChatInput";
import ErrorBanner from "./components/ErrorBanner";
import { CloudSun } from "lucide-react";

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
  const [sessionId] = useState(getOrCreateSessionId);
  const bottomRef = useRef(null);

  // Auto-scroll to bottom on new messages / loading state change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = useCallback(
    async (overrideText) => {
      const text = (overrideText ?? inputValue).trim();
      if (!text || isLoading) return;

      setError(null);
      setInputValue("");
      setMessages((prev) => [
        ...prev,
        { id: uuidv4(), role: "user", content: text },
      ]);
      setIsLoading(true);

      try {
        const data = await sendMessage(text, sessionId);
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
              intent: data.intent,
              city: data.city,
            },
          },
        ]);
      } catch (err) {
        const detail =
          err?.response?.data?.detail ||
          err?.message ||
          "Something went wrong. Please try again.";
        setError(detail);
      } finally {
        setIsLoading(false);
      }
    },
    [inputValue, isLoading, sessionId]
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
      <Header onClear={handleClear} />

      {/* Messages area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">

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
        disabled={isLoading}
      />
    </div>
  );
}
