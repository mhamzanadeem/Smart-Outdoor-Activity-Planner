import { AlertTriangle, X } from "lucide-react";

export default function ErrorBanner({ error, onDismiss }) {
  if (!error) return null;
  return (
    <div className="flex items-start gap-3 px-4 py-3 bg-red-950/70 border border-red-800 rounded-xl text-sm text-red-300 animate-fade-in">
      <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-red-400" />
      <span className="flex-1">{error}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 hover:text-red-100 transition-colors"
          aria-label="Dismiss error"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
