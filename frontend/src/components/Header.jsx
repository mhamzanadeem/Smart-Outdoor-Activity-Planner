import { CloudSun, Zap } from "lucide-react";

export default function Header({ onClear, serverStatus }) {
  const isActive = serverStatus === "active";
  const isWaking = serverStatus === "waking" || serverStatus === "checking";

  const statusClass = isActive
    ? "bg-emerald-900/40 border-emerald-800/60 text-emerald-400"
    : isWaking
    ? "bg-amber-900/40 border-amber-800/60 text-amber-400"
    : "bg-red-900/40 border-red-800/60 text-red-400";

  const dotClass = isActive
    ? "bg-emerald-400 animate-pulse"
    : isWaking
    ? "bg-amber-400 animate-pulse"
    : "bg-red-400";

  const statusText = isActive ? "Server Active" : isWaking ? "Waking Server" : "Server Sleeping";

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
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs ${statusClass}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
          {statusText}
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
