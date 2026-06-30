export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 animate-fade-in">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-brand-700 border border-brand-500 flex items-center justify-center text-xs font-bold text-brand-200 select-none">
        SW
      </div>
      {/* Bubble */}
      <div className="chat-bubble-agent flex items-center gap-1 py-3.5 px-5">
        <span
          className="w-2 h-2 rounded-full bg-gray-400 typing-dot animate-typing-dot"
          style={{ animationDelay: "-0.32s" }}
        />
        <span
          className="w-2 h-2 rounded-full bg-gray-400 typing-dot animate-typing-dot"
          style={{ animationDelay: "-0.16s" }}
        />
        <span
          className="w-2 h-2 rounded-full bg-gray-400 typing-dot animate-typing-dot"
          style={{ animationDelay: "0s" }}
        />
      </div>
    </div>
  );
}
