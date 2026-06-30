import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Cpu,
  Wrench,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";

function ToolExecution({ execution }) {
  const [open, setOpen] = useState(false);
  const isSuccess = execution.status === "success";

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-750 transition-colors text-left"
      >
        {isSuccess ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
        ) : (
          <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
        )}
        <span className="font-mono text-xs text-amber-300 font-medium flex-1">
          {execution.tool_name}
        </span>
        {execution.duration_ms && (
          <span className="flex items-center gap-1 text-xs text-gray-500 font-mono">
            <Clock className="w-3 h-3" />
            {execution.duration_ms}ms
          </span>
        )}
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
        )}
      </button>

      {open && (
        <div className="p-3 bg-gray-900 space-y-2 text-xs font-mono">
          <div>
            <span className="text-gray-500 uppercase tracking-wide text-[10px]">
              Input
            </span>
            <pre className="mt-1 text-emerald-300 whitespace-pre-wrap break-all">
              {JSON.stringify(execution.input, null, 2)}
            </pre>
          </div>
          {execution.output && (
            <div>
              <span className="text-gray-500 uppercase tracking-wide text-[10px]">
                Output
              </span>
              <pre className="mt-1 text-brand-300 whitespace-pre-wrap break-all">
                {JSON.stringify(execution.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ThinkingPanel({ toolExecutions = [], reasoning = "", intent = null }) {
  const [showReasoning, setShowReasoning] = useState(false);

  if (!toolExecutions.length && !reasoning) return null;

  return (
    <div className="mt-3 space-y-2 animate-fade-in">
      {/* Tool Executions */}
      {toolExecutions.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs text-gray-500 font-medium">
            <Wrench className="w-3.5 h-3.5" />
            <span>Tool Calls</span>
            {intent && (
              <span className="ml-auto tool-badge bg-brand-900/60 text-brand-300 border border-brand-800">
                {intent}
              </span>
            )}
          </div>
          {toolExecutions.map((exec, i) => (
            <ToolExecution key={i} execution={exec} />
          ))}
        </div>
      )}

      {/* Reasoning */}
      {reasoning && (
        <div>
          <button
            onClick={() => setShowReasoning((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors font-medium"
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>Agent Reasoning</span>
            {showReasoning ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
          </button>
          {showReasoning && (
            <div className="mt-2 p-3 bg-gray-900 border border-gray-700 rounded-lg text-xs text-gray-400 leading-relaxed italic animate-fade-in">
              {reasoning}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
