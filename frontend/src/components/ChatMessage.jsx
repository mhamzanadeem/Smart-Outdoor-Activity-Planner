import WeatherCard from "./WeatherCard";
import ThinkingPanel from "./ThinkingPanel";
import { User, AlertTriangle } from "lucide-react";

function formatText(text) {
  // Simple markdown-like: bold **text**, newlines to <br>
  return text.split("\n").map((line, i) => {
    const parts = line.split(/\*\*(.*?)\*\*/g);
    return (
      <span key={i}>
        {parts.map((part, j) =>
          j % 2 === 1 ? <strong key={j}>{part}</strong> : part
        )}
        {i < text.split("\n").length - 1 && <br />}
      </span>
    );
  });
}

// Maps error_code to a setup hint shown below the message
const ERROR_HINTS = {
  llm_auth_error: "Get a free key at console.groq.com → set LLM_API_KEY in backend/.env → restart uvicorn",
  llm_api_key_missing: "Set LLM_API_KEY in backend/.env → restart uvicorn",
  llm_rate_limit: "Wait a few seconds, then try again",
  llm_unavailable: "Check LLM_API_BASE_URL in backend/.env or try again later",
  weather_api_missing: "Get a free key at openweathermap.org → set WEATHER_API_KEY in backend/.env → restart uvicorn",
  weather_city_not_found: "Try a different city name (e.g. 'London', 'Rawalpindi')",
  weather_fetch_error: "Check your internet connection or try again later",
  weather_network_error: "Check your internet connection",
};

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex items-end justify-end gap-2 animate-fade-in">
        <div className="chat-bubble-user">
          <p className="text-sm leading-relaxed">{message.content}</p>
        </div>
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 border border-gray-600 flex items-center justify-center">
          <User className="w-4 h-4 text-gray-300" />
        </div>
      </div>
    );
  }

  // Inline error bubble (API config errors, etc.)
  if (message.role === "error") {
    const errorCode = message.metadata?.error_code;
    const hint = ERROR_HINTS[errorCode];
    return (
      <div className="flex items-start gap-2 animate-slide-up">
        {/* Error avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-red-900/60 border border-red-700 flex items-center justify-center">
          <AlertTriangle className="w-4 h-4 text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="rounded-2xl rounded-tl-sm bg-red-950/60 border border-red-800/70 px-4 py-3 space-y-2">
            <p className="text-sm leading-relaxed text-red-200">{message.content}</p>
            {hint && (
              <p className="text-xs text-red-400/80 leading-relaxed">
                <span className="font-semibold">Fix: </span>{hint}
              </p>
            )}
            {errorCode && (
              <span className="inline-block text-[10px] font-mono bg-red-900/50 text-red-500 px-2 py-0.5 rounded-full border border-red-800/50">
                {errorCode}
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Agent message
  const { content, metadata } = message;
  const hasMetadata = metadata && (metadata.tool_called || metadata.reasoning);
  const weatherItems =
    metadata?.weather_data_list?.length > 0
      ? metadata.weather_data_list
      : metadata?.weather_data
      ? [metadata.weather_data]
      : [];

  return (
    <div className="flex items-start gap-2 animate-slide-up">
      {/* Agent avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-brand-700 border border-brand-500 flex items-center justify-center text-xs font-bold text-brand-200 select-none">
        SW
      </div>

      <div className="flex-1 min-w-0">
        {/* Main answer bubble */}
        <div className="chat-bubble-agent">
          <p className="text-sm leading-relaxed">{formatText(content)}</p>

          {/* Weather card inside the bubble */}
          {weatherItems.map((item, idx) => (
            <WeatherCard key={`${item.city || "city"}-${idx}`} data={item} />
          ))}
        </div>

        {/* Tool executions + reasoning (below bubble) */}
        {hasMetadata && (
          <ThinkingPanel
            toolExecutions={metadata.tool_executions || []}
            reasoning={metadata.reasoning || ""}
            intent={metadata.intent}
          />
        )}
      </div>
    </div>
  );
}

