const cliCommands = [
  { command: "dataforge init", description: "Initialize a new dataforge project", args: "[--path]" },
  { command: "dataforge run", description: "Run a pipeline from natural language", args: '"<task description>"' },
  { command: "dataforge list", description: "List configured agents", args: "[--json]" },
  { command: "dataforge status", description: "Show pipeline status", args: "[<id>]" },
  { command: "dataforge logs", description: "View agent logs", args: "[--tail]" },
];

const apiEndpoints = [
  { method: "GET", path: "/api/agents", description: "List all registered agents" },
  { method: "GET", path: "/api/pipelines", description: "List all pipeline runs" },
  { method: "GET", path: "/api/pipelines/<id>/results", description: "Get pipeline results" },
  { method: "GET", path: "/api/pipelines/stream", description: "SSE stream of pipeline updates" },
  { method: "POST", path: "/api/pipelines", description: "Create a new pipeline run" },
];

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      <main className="max-w-3xl mx-auto px-6 py-16 sm:py-24">
        {/* Header */}
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4 text-slate-900 dark:text-white">
          Documentation
        </h1>
        <p className="text-lg text-slate-500 dark:text-slate-400 mb-16">
          Get started with mcp-dataforge in minutes.
        </p>

        {/* Quick Start */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold tracking-tight mb-6 text-slate-900 dark:text-white">
            Quick Start
          </h2>

          <div className="space-y-8">
            <div>
              <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                1. Install
              </h3>
              <div className="rounded-xl bg-slate-900 dark:bg-slate-800 px-5 py-4 overflow-x-auto">
                <code className="text-sm font-mono text-white leading-relaxed block">
                  pip install mcp-dataforge
                </code>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                2. Initialize
              </h3>
              <div className="rounded-xl bg-slate-900 dark:bg-slate-800 px-5 py-4 overflow-x-auto">
                <code className="text-sm font-mono text-white leading-relaxed block">
                  dataforge init
                </code>
              </div>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Creates a <code className="text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-xs font-mono">dataforge.toml</code> configuration file and registers default agents.
              </p>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                3. Run a pipeline
              </h3>
              <div className="rounded-xl bg-slate-900 dark:bg-slate-800 px-5 py-4 overflow-x-auto">
                <code className="text-sm font-mono text-white leading-relaxed block">
                  dataforge run &quot;Find null values in orders table, fix schema drift, add validation rules&quot;
                </code>
              </div>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Natural language is decomposed into a multi-step pipeline and executed by specialist agents.
              </p>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                4. Monitor
              </h3>
              <div className="rounded-xl bg-slate-900 dark:bg-slate-800 px-5 py-4 overflow-x-auto">
                <code className="text-sm font-mono text-white leading-relaxed block">
                  dataforge status<br />
                  dataforge logs --tail
                </code>
              </div>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Track pipeline progress and inspect agent outputs in real time.
              </p>
            </div>
          </div>
        </section>

        {/* CLI Reference */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold tracking-tight mb-6 text-slate-900 dark:text-white">
            CLI Reference
          </h2>
          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
                  <th className="text-left px-5 py-3 font-semibold text-slate-600 dark:text-slate-300">Command</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600 dark:text-slate-300">Description</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600 dark:text-slate-300">Arguments</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {cliCommands.map((cmd) => (
                  <tr key={cmd.command} className="hover:bg-slate-50 dark:hover:bg-slate-900/50">
                    <td className="px-5 py-3">
                      <code className="text-xs font-mono text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950 px-2 py-0.5 rounded">
                        {cmd.command}
                      </code>
                    </td>
                    <td className="px-5 py-3 text-slate-600 dark:text-slate-300">{cmd.description}</td>
                    <td className="px-5 py-3 text-slate-400 dark:text-slate-500 text-xs font-mono">{cmd.args}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* API Endpoints */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold tracking-tight mb-6 text-slate-900 dark:text-white">
            API Endpoints
          </h2>
          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
                  <th className="text-left px-5 py-3 font-semibold text-slate-600 dark:text-slate-300">Method</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600 dark:text-slate-300">Path</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600 dark:text-slate-300">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {apiEndpoints.map((ep) => (
                  <tr key={ep.path} className="hover:bg-slate-50 dark:hover:bg-slate-900/50">
                    <td className="px-5 py-3">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                        ep.method === "GET"
                          ? "bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400"
                          : "bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400"
                      }`}>
                        {ep.method}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <code className="text-xs font-mono text-slate-800 dark:text-slate-200">{ep.path}</code>
                    </td>
                    <td className="px-5 py-3 text-slate-600 dark:text-slate-300">{ep.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
