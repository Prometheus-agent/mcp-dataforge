"use client";

import { useEffect, useState, useCallback } from "react";
import type { AgentInfo, PipelineSummary } from "@/types";
import { DAGView } from "@/components/DAGView";

const AGENT_ICONS: Record<string, string> = {
  pipeline: "🔧", dq: "✅", schema: "📐",
  catalog: "📚", observability: "🔍", orchestration: "⚡",
};

const AGENT_COLORS: Record<string, string> = {
  pipeline: "bg-blue-50 dark:bg-blue-950 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200",
  dq: "bg-emerald-50 dark:bg-emerald-950 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200",
  schema: "bg-violet-50 dark:bg-violet-950 border-violet-300 dark:border-violet-700 text-violet-800 dark:text-violet-200",
  catalog: "bg-amber-50 dark:bg-amber-950 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-200",
  observability: "bg-rose-50 dark:bg-rose-950 border-rose-300 dark:border-rose-700 text-rose-800 dark:text-rose-200",
  orchestration: "bg-cyan-50 dark:bg-cyan-950 border-cyan-300 dark:border-cyan-700 text-cyan-800 dark:text-cyan-200",
};

export default function DashboardPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [pipelines, setPipelines] = useState<PipelineSummary[]>([]);
  const [tab, setTab] = useState<"overview" | "pipelines" | "agents">("overview");
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);
  const [expandedPipeline, setExpandedPipeline] = useState<string | null>(null);
  const [dark, setDark] = useState(false);
  const [live, setLive] = useState(true);
  const [selectedPipelineDetail, setSelectedPipelineDetail] = useState<any>(null);

  useEffect(() => {
    const stored = localStorage.getItem("dataforge-dark");
    if (stored === "true" || (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      setDark(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("dataforge-dark", String(dark));
  }, [dark]);

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

  useEffect(() => {
    const source = new EventSource("/api/pipelines/stream");
    source.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setPipelines(data);
      } catch {}
    };
    source.onerror = () => setLive(false);
    return () => source.close();
  }, []);

  async function showPipelineDetail(pipelineId: string) {
    try {
      const r = await fetch(`/api/pipelines/${pipelineId}/results`);
      const data = await r.json();
      setSelectedPipelineDetail(data);
    } catch {}
  }

  const stats = {
    total: pipelines.length,
    completed: pipelines.filter(p => p.status === "completed").length,
    errors: pipelines.filter(p => p.status !== "completed" && p.status !== "planned").length,
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/90 dark:bg-slate-800/90 backdrop-blur border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center h-14 gap-8">
          <h1 className="text-lg font-bold tracking-tight">⚒️ dataforge</h1>
          {(["overview", "pipelines", "agents"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`text-sm font-medium capitalize ${tab === t ? "text-blue-600 dark:text-blue-400" : "text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"}`}>{t}</button>
          ))}
          <div className="ml-auto flex items-center gap-3 text-xs text-slate-400 dark:text-slate-500">
            <span className={`w-2 h-2 rounded-full ${live ? 'bg-green-500' : 'bg-red-500'}`} title={live ? 'Live' : 'Disconnected'} />
            <button onClick={() => setDark(d => !d)} className="text-lg leading-none hover:opacity-80 transition-opacity" aria-label="Toggle dark mode">
              {dark ? "☀️" : "🌙"}
            </button>
            <span>{agents.length} agents</span>
          </div>
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
              <div key={c.label} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
                <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{c.label}</div>
                <div className="text-3xl font-bold mt-0.5 dark:text-slate-100">{c.value}</div>
                <div className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{c.sub}</div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold dark:text-slate-100">Recent Pipelines</h2>
            <button onClick={() => setTab("pipelines")} className="text-xs text-blue-600 dark:text-blue-400 hover:underline">View all</button>
          </div>
          <div className="space-y-2 mb-10">
            {pipelines.length === 0
              ? <EmptyState msg="No pipelines yet. Run a task from Claude Code!" />
              : pipelines.slice(-5).reverse().map(p => <PipelineRowSmall key={p.id} p={p} onResults={showPipelineDetail} />)}
          </div>

          <h2 className="text-base font-semibold mb-4 dark:text-slate-100">Agents</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {agents.map(a => <AgentCard key={a.name} agent={a} onClick={() => { setSelectedAgent(a); setTab("agents"); }} />)}
          </div>
        </>}

        {/* ──── PIPELINES ──── */}
        {tab === "pipelines" && <>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold dark:text-slate-100">All Pipelines</h2>
            <span className="text-sm text-slate-500 dark:text-slate-400">{pipelines.length} total</span>
          </div>
          <div className="space-y-2">
            {pipelines.length === 0
              ? <EmptyState msg="No pipelines yet." />
              : pipelines.slice().reverse().map(p => (
                <div key={p.id}>
                  <button onClick={() => setExpandedPipeline(expandedPipeline === p.id ? null : p.id)}
                    className="w-full flex items-center gap-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-3 text-left hover:border-slate-300 dark:hover:border-slate-600 transition-colors">
                    <StatusBadge status={p.status} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{p.task || "—"}</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {(p.plan || []).map((s, i) => (
                          <span key={i} className="text-[10px] bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded">{s.agent}</span>
                        ))}
                      </div>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); showPipelineDetail(p.id); setExpandedPipeline(p.id); }}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:underline shrink-0">
                      Results
                    </button>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">{p.id.slice(0,12)}</span>
                    <svg className={`w-4 h-4 text-slate-400 shrink-0 transition-transform ${expandedPipeline === p.id ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {expandedPipeline === p.id && (
                    <div className="mt-2 mb-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
                      <h4 className="text-sm font-semibold mb-3 dark:text-slate-100">Pipeline DAG</h4>
                      <div className="h-64 w-full"><DAGView plan={p.plan || []} /></div>
                      {selectedPipelineDetail && selectedPipelineDetail.pipeline_id === p.id && (
                        <div className="mt-4">
                          <h5 className="text-sm font-semibold mb-2 dark:text-slate-100">Agent Results</h5>
                          <div className="space-y-2">
                            {selectedPipelineDetail.agent_results?.map((ar: any, i: number) => (
                              <div key={i} className="flex items-center gap-3 bg-slate-50 dark:bg-slate-900 rounded-lg p-3 text-sm">
                                <span className="text-lg">
                                  {ar.status === 'success' ? '✅' : '❌'}
                                </span>
                                <span className="font-medium capitalize">{ar.agent}</span>
                                <span className="text-slate-500 text-xs">{ar.step_task || ar.status}</span>
                                {ar.result_summary && (
                                  <pre className="ml-auto text-[10px] text-slate-400">{JSON.stringify(ar.result_summary)}</pre>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
          </div>
        </>}

        {/* ──── AGENTS ──── */}
        {tab === "agents" && <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3">
            <h2 className="text-base font-semibold mb-4 dark:text-slate-100">Specialist Agents</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {agents.map(a => (
                <AgentCard key={a.name} agent={a} onClick={() => setSelectedAgent(selectedAgent?.name === a.name ? null : a)} selected={selectedAgent?.name === a.name} />
              ))}
            </div>
          </div>
          {selectedAgent && (
            <div className="lg:col-span-1">
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 sticky top-20">
                <div className="text-3xl mb-1">{AGENT_ICONS[selectedAgent.name] || "🤖"}</div>
                <h3 className="text-lg font-bold capitalize dark:text-slate-100">{selectedAgent.name}</h3>
                <div className="flex flex-wrap gap-1.5 mt-3 mb-4">
                  {selectedAgent.capabilities.map(c => (
                    <span key={c} className="text-[11px] bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded-md font-medium">{c}</span>
                  ))}
                </div>
                <pre className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-3 text-xs font-mono overflow-auto max-h-80 text-slate-600 dark:text-slate-300">
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
  const cls = status === "completed" ? "bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300" :
    status === "planned" ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300" : "bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300";
  return <span className={`shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${cls}`}>{status}</span>;
}

function EmptyState({ msg }: { msg: string }) {
  return <div className="text-center py-16 text-slate-400 dark:text-slate-500"><p>{msg}</p></div>;
}

function PipelineRowSmall({ p, onResults }: { p: PipelineSummary; onResults?: (id: string) => void }) {
  return (
    <div className="flex items-center gap-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-3">
      <StatusBadge status={p.status} />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate dark:text-slate-100">{p.task || "—"}</div>
        <div className="flex flex-wrap gap-1 mt-1">
          {(p.plan || []).map((s, i) => (
            <span key={i} className="text-[10px] bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded">{s.agent}</span>
          ))}
        </div>
      </div>
      {onResults && (
        <button onClick={(e) => { e.stopPropagation(); onResults(p.id); }}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline shrink-0">
          Results
        </button>
      )}
      <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">{p.id.slice(0,12)}</span>
    </div>
  );
}

function AgentCard({ agent, onClick, selected }: { agent: AgentInfo; onClick: () => void; selected?: boolean }) {
  const colorClass = AGENT_COLORS[agent.name] || "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300";
  return (
    <button onClick={onClick} className={`text-left p-3 rounded-xl border transition-all ${selected ? "ring-2 ring-blue-500 shadow-md scale-[1.02]" : "hover:shadow-sm"} ${colorClass}`}>
      <div className="text-2xl">{AGENT_ICONS[agent.name] || "🤖"}</div>
      <div className="font-semibold text-sm mt-1 capitalize">{agent.name}</div>
      <div className="flex flex-wrap gap-1 mt-1.5">
        {agent.capabilities.slice(0, 2).map(c => <span key={c} className="text-[10px] bg-white/60 dark:bg-black/20 px-1.5 py-0.5 rounded">{c}</span>)}
        {agent.capabilities.length > 2 && <span className="text-[10px] text-slate-400 dark:text-slate-500">+{agent.capabilities.length - 2}</span>}
      </div>
    </button>
  );
}
