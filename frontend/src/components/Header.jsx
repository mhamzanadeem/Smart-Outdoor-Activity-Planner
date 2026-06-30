import { CloudSun, Zap } from "lucide-react";

export default function Header({ onClear }) {
  return (
    <header className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-950/80 backdrop-blur-md sticky top-0 z-10">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-xl bg-brand-700 flex items-center justify-center shadow-lg shadow-brand-900/50">
          <CloudSun className="w-5 h-5 text-brand-200" />
        </div>
        <div>
          <h1 className="font-bold text-white text-base leading-none">SkyWise</h1>
          <p className="text-[10px] text-gray-500 leading-none mt-0.5 flex items-center gap-1">
            <Zap className="w-2.5 h-2.5 text-brand-400" />
            AI Weather &amp; Activity Planner
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-900/40 border border-emerald-800/60 text-emerald-400 text-xs">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Live Weather
        </div>
        <button
          onClick={onClear}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2 py-1 rounded-lg hover:bg-gray-800"
        >
          Clear
        </button>
      </div>
    </header>
  );
}
