import Link from "next/link";

const agents = [
  { icon: "🔧", name: "Pipeline", desc: "SQL, Python, Spark" },
  { icon: "✅", name: "Data Quality", desc: "Profiling, anomalies" },
  { icon: "📐", name: "Schema", desc: "Drift, migration" },
  { icon: "⚡", name: "Orchestration", desc: "DAGs, scheduling" },
  { icon: "📚", name: "Catalog", desc: "Discovery, docs" },
  { icon: "🔍", name: "Observability", desc: "Monitoring, cost" },
];

const stats = [
  { label: "MCP", sub: "Native protocol" },
  { label: "6", sub: "Specialist agents" },
  { label: "Python", sub: "First-class" },
  { label: "Ext", sub: "Plugin architecture" },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      <main className="max-w-4xl mx-auto px-6 py-20 sm:py-28">
        {/* Hero */}
        <section className="mb-20">
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tighter leading-[1.05] mb-6 text-slate-900 dark:text-white">
            The MCP-native<br />
            DE agent framework
          </h1>
          <p className="text-lg sm:text-xl text-slate-500 dark:text-slate-400 max-w-xl leading-relaxed mb-10">
            Natural language for pipelines. Multi-agent execution
            through MCP. 6 specialist agents collaborate to build,
            validate, and monitor your data infrastructure.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <code className="inline-flex items-center px-5 py-3 rounded-xl bg-slate-900 dark:bg-slate-800 text-white font-mono text-sm font-semibold shadow-sm">
              pip install mcp-dataforge
            </code>
            <Link
              href="/docs"
              className="inline-flex items-center px-5 py-3 rounded-xl border border-slate-200 dark:border-slate-700 font-medium text-sm text-slate-600 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-600 transition-colors"
            >
              Read docs &rarr;
            </Link>
          </div>
        </section>

        {/* Demo Card */}
        <section className="mb-20">
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 overflow-hidden">
            <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-200 dark:border-slate-800">
              <span className="bg-slate-900 dark:bg-slate-700 text-white text-[11px] font-semibold px-3 py-1 rounded-full uppercase tracking-wider">
                Demo
              </span>
              <span className="text-sm text-slate-400 dark:text-slate-500">
                Try it in Claude Code
              </span>
            </div>
            <div className="px-5 py-4 font-mono text-sm leading-loose text-slate-800 dark:text-slate-200">
              <span className="text-slate-400">$ </span>
              dataforge run &ldquo;Find nulls in orders, fix schema drift, add validation&rdquo;
              <br />
              <span className="text-blue-500">&rarr;</span> 3 agents activated<br />
              <span className="text-blue-500">&rarr;</span> Schema drift detected: 2 columns<br />
              <span className="text-blue-500">&rarr;</span> 7 null violations fixed<br />
              <span className="text-blue-500">&rarr;</span> 12 validation rules added
            </div>
          </div>
        </section>

        {/* Agent Grid */}
        <section className="mb-20">
          <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400 dark:text-slate-500 mb-5">
            Specialist agents
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-px bg-slate-200 dark:bg-slate-800 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800">
            {agents.map((a) => (
              <div
                key={a.name}
                className="bg-white dark:bg-slate-950 p-5 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
              >
                <div className="text-2xl mb-2">{a.icon}</div>
                <div className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                  {a.name}
                </div>
                <div className="text-sm text-slate-500 dark:text-slate-400">
                  {a.desc}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Stats */}
        <section className="mb-20">
          <div className="flex flex-wrap gap-x-12 gap-y-6">
            {stats.map((s) => (
              <div key={s.label}>
                <div className="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white">
                  {s.label}
                </div>
                <div className="text-sm text-slate-400 dark:text-slate-500 mt-0.5">
                  {s.sub}
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="max-w-4xl mx-auto px-6 pb-8">
        <div className="border-t border-slate-200 dark:border-slate-800 pt-6 flex flex-wrap items-center justify-between gap-4 text-sm text-slate-400 dark:text-slate-500">
          <span>&#x2692;&#xFE0F; mcp-dataforge</span>
          <span>Apache 2.0</span>
        </div>
      </footer>
    </div>
  );
}
