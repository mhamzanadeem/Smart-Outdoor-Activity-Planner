import WeatherCard from "./WeatherCard";
import ThinkingPanel from "./ThinkingPanel";
import { User } from "lucide-react";

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

  // Agent message
  const { content, metadata } = message;
  const hasMetadata = metadata && (metadata.tool_called || metadata.reasoning);

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
          {metadata?.weather_data && (
            <WeatherCard data={metadata.weather_data} />
          )}
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
