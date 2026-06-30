const SUGGESTIONS = [
  "Can I play cricket tomorrow?",
  "Is it good weather for hiking today?",
  "Should I carry an umbrella?",
  "What should I wear today?",
  "Is it safe to drive tonight?",
  "Can I go cycling this evening?",
  "Will it be too hot for a run?",
  "Is the visibility good for driving?",
];

export default function SuggestionPills({ onSelect }) {
  return (
    <div className="flex flex-wrap gap-2 justify-center px-4">
      {SUGGESTIONS.map((s) => (
        <button
          key={s}
          onClick={() => onSelect(s)}
          className="px-3 py-1.5 text-xs rounded-full bg-gray-800 border border-gray-700 text-gray-300 hover:bg-gray-700 hover:border-brand-600 hover:text-brand-300 transition-all duration-150 active:scale-95"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
