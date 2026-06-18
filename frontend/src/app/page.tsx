"use client";

import { useEffect, useState, useCallback } from "react";
import type { AgentInfo, PipelineSummary } from "@/types";
import { DAGView } from "@/components/DAGView";

const AGENT_ICONS: Record<string, string> = {
  pipeline: "🔧", dq: "✅", schema: "📐",
  catalog: "📚", observability: "🔍", orchestration: "⚡",
};

const AGENT_COLORS: Record<string, string> = {
  pipeline: "bg-blue-50 border-blue-300 text-blue-800",
  dq: "bg-emerald-50 border-emerald-300 text-emerald-800",
  schema: "bg-violet-50 border-violet-300 text-violet-800",
  catalog: "bg-amber-50 border-amber-300 text-amber-800",
  observability: "bg-rose-50 border-rose-300 text-rose-800",
  orchestration: "bg-cyan-50 border-cyan-300 text-cyan-800",
};

export default function Home() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [pipelines, setPipelines] = useState<PipelineSummary[]>([]);
  const [tab, setTab] = useState<"overview" | "pipelines" | "agents">("overview");
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);
  const [expandedPipeline, setExpandedPipeline] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [a, p] = await Promise.all([
        fetch("/api/agents").then(r => r.json()),
        fetch("/api/pipelines").then(r => r.json()),
      ]);
      setAgents(a);
      setPipelines(p.pipelines || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadData(); const i = setInterval(loadData, 5000); return () => clearInterval(i); }, [loadData]);

  const stats = {
    total: pipelines.length,
    completed: pipelines.filter(p => p.status === "completed").length,
    errors: pipelines.filter(p => p.status !== "completed" && p.status !== "planned").length,
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center h-14 gap-8">
          <h1 className="text-lg font-bold tracking-tight">⚒️ dataforge</h1>
          {(["overview", "pipelines", "agents"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`text-sm font-medium capitalize ${tab === t ? "text-blue-600" : "text-slate-500 hover:text-slate-800"}`}>{t}</button>
          ))}
          <div className="ml-auto text-xs text-slate-400">{agents.length} agents</div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

        {/* ──── OVERVIEW ──── */}
        {tab === "overview" && <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[
              { label: "Pipelines", value: stats.total, sub: "All time" },
              { label: "Agents", value: agents.length, sub: "Specialist agents" },
              { label: "Completed", value: stats.completed, sub: `${stats.total ? Math.round(stats.completed/stats.total*100) : 0}% pass` },
              { label: "Errors", value: stats.errors, sub: `${stats.total ? Math.round(stats.errors/stats.total*100) : 0}% fail` },
            ].map(c => (
              <div key={c.label} className="bg-white border border-slate-200 rounded-xl p-4">
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">{c.label}</div>
                <div className="text-3xl font-bold mt-0.5">{c.value}</div>
                <div className="text-sm text-slate-500 mt-0.5">{c.sub}</div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">Recent Pipelines</h2>
            <button onClick={() => setTab("pipelines")} className="text-xs text-blue-600 hover:underline">View all</button>
          </div>
          <div className="space-y-2 mb-10">
            {pipelines.length === 0
              ? <EmptyState msg="No pipelines yet. Run a task from Claude Code!" />
              : pipelines.slice(-5).reverse().map(p => <PipelineRowSmall key={p.id} p={p} />)}
          </div>

          <h2 className="text-base font-semibold mb-4">Agents</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {agents.map(a => <AgentCard key={a.name} agent={a} onClick={() => { setSelectedAgent(a); setTab("agents"); }} />)}
          </div>
        </>}

        {/* ──── PIPELINES ──── */}
        {tab === "pipelines" && <>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">All Pipelines</h2>
            <span className="text-sm text-slate-500">{pipelines.length} total</span>
          </div>
          <div className="space-y-2">
            {pipelines.length === 0
              ? <EmptyState msg="No pipelines yet." />
              : pipelines.slice().reverse().map(p => (
                <div key={p.id}>
                  <button onClick={() => setExpandedPipeline(expandedPipeline === p.id ? null : p.id)}
                    className="w-full flex items-center gap-3 bg-white border border-slate-200 rounded-lg px-4 py-3 text-left hover:border-slate-300 transition-colors">
                    <StatusBadge status={p.status} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{p.task || "—"}</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {(p.plan || []).map((s, i) => (
                          <span key={i} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{s.agent}</span>
                        ))}
                      </div>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">{p.id.slice(0,12)}</span>
                    <svg className={`w-4 h-4 text-slate-400 shrink-0 transition-transform ${expandedPipeline === p.id ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {expandedPipeline === p.id && (
                    <div className="mt-2 mb-4 bg-white border border-slate-200 rounded-lg p-4">
                      <h4 className="text-sm font-semibold mb-3">Pipeline DAG</h4>
                      <div className="h-64 w-full"><DAGView plan={p.plan || []} /></div>
                    </div>
                  )}
                </div>
              ))}
          </div>
        </>}

        {/* ──── AGENTS ──── */}
        {tab === "agents" && <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3">
            <h2 className="text-base font-semibold mb-4">Specialist Agents</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {agents.map(a => (
                <AgentCard key={a.name} agent={a} onClick={() => setSelectedAgent(selectedAgent?.name === a.name ? null : a)} selected={selectedAgent?.name === a.name} />
              ))}
            </div>
          </div>
          {selectedAgent && (
            <div className="lg:col-span-1">
              <div className="bg-white border border-slate-200 rounded-xl p-5 sticky top-20">
                <div className="text-3xl mb-1">{AGENT_ICONS[selectedAgent.name] || "🤖"}</div>
                <h3 className="text-lg font-bold capitalize">{selectedAgent.name}</h3>
                <div className="flex flex-wrap gap-1.5 mt-3 mb-4">
                  {selectedAgent.capabilities.map(c => (
                    <span key={c} className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md font-medium">{c}</span>
                  ))}
                </div>
                <pre className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs font-mono overflow-auto max-h-80 text-slate-600">
                  {JSON.stringify(selectedAgent, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>}
      </main>
    </div>
  );
}

/* ─── Components ─── */

function StatusBadge({ status }: { status: string }) {
  const cls = status === "completed" ? "bg-emerald-100 text-emerald-700" :
    status === "planned" ? "bg-blue-100 text-blue-700" : "bg-red-100 text-red-700";
  return <span className={`shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${cls}`}>{status}</span>;
}

function EmptyState({ msg }: { msg: string }) {
  return <div className="text-center py-16 text-slate-400"><p>{msg}</p></div>;
}

function PipelineRowSmall({ p }: { p: PipelineSummary }) {
  return (
    <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-lg px-4 py-3">
      <StatusBadge status={p.status} />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{p.task || "—"}</div>
        <div className="flex flex-wrap gap-1 mt-1">
          {(p.plan || []).map((s, i) => (
            <span key={i} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{s.agent}</span>
          ))}
        </div>
      </div>
      <span className="text-[10px] text-slate-400 font-mono">{p.id.slice(0,12)}</span>
    </div>
  );
}

function AgentCard({ agent, onClick, selected }: { agent: AgentInfo; onClick: () => void; selected?: boolean }) {
  const colorClass = AGENT_COLORS[agent.name] || "bg-slate-50 border-slate-200 text-slate-700";
  return (
    <button onClick={onClick} className={`text-left p-3 rounded-xl border transition-all ${selected ? "ring-2 ring-blue-500 shadow-md scale-[1.02]" : "hover:shadow-sm"} ${colorClass}`}>
      <div className="text-2xl">{AGENT_ICONS[agent.name] || "🤖"}</div>
      <div className="font-semibold text-sm mt-1 capitalize">{agent.name}</div>
      <div className="flex flex-wrap gap-1 mt-1.5">
        {agent.capabilities.slice(0, 2).map(c => <span key={c} className="text-[10px] bg-white/60 px-1.5 py-0.5 rounded">{c}</span>)}
        {agent.capabilities.length > 2 && <span className="text-[10px] text-slate-400">+{agent.capabilities.length - 2}</span>}
      </div>
    </button>
  );
}
