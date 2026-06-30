import { useRef, useEffect } from "react";
import { Send } from "lucide-react";

export default function ChatInput({ value, onChange, onSubmit, disabled }) {
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [value]);

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSubmit();
    }
  }

  return (
    <div className="flex items-end gap-2 p-4 border-t border-gray-800 bg-gray-950">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask about weather, activities, clothing, driving…"
          rows={1}
          className="w-full resize-none bg-gray-800 border border-gray-700 focus:border-brand-500 focus:ring-1 focus:ring-brand-500/40 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 outline-none transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed leading-relaxed"
        />
      </div>
      <button
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        className="flex-shrink-0 w-11 h-11 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-gray-700 disabled:text-gray-500 text-white flex items-center justify-center transition-all duration-150 active:scale-95 shadow-lg shadow-brand-900/30"
        aria-label="Send message"
      >
        <Send className="w-4 h-4" />
      </button>
    </div>
  );
}
