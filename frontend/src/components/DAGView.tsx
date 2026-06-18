"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

interface PlanStep {
  agent: string;
  tool?: string;
  params?: Record<string, unknown>;
  depends_on?: string[];
  parallel?: boolean;
}

const AGENT_COLORS: Record<string, string> = {
  pipeline: "#3b82f6",
  dq: "#10b981",
  schema: "#8b5cf6",
  catalog: "#f59e0b",
  observability: "#f43f5e",
  orchestration: "#06b6d4",
};

const AGENT_ICONS: Record<string, string> = {
  pipeline: "🔧",
  dq: "✅",
  schema: "📐",
  catalog: "📚",
  observability: "🔍",
  orchestration: "⚡",
};

export function DAGView({ plan }: { plan: PlanStep[] }) {
  const { nodes, edges } = useMemo(() => {
    if (!plan || plan.length === 0) {
      return { nodes: [], edges: [] };
    }

    const n: Node[] = [];
    const e: Edge[] = [];
    const sorted = [...plan];

    sorted.forEach((step, i) => {
      const agentName = step.agent || "unknown";
      const color = AGENT_COLORS[agentName] || "#64748b";
      const icon = AGENT_ICONS[agentName] || "🤖";
      const isParallel = step.parallel;

      n.push({
        id: `step-${i}`,
        type: "default",
        position: { x: 220 * i, y: 0 },
        data: {
          label: (
            <div className="flex flex-col items-center gap-1 px-2 py-1.5 min-w-[120px]">
              <span className="text-lg">{icon}</span>
              <span className="text-xs font-semibold capitalize">{agentName}</span>
              <span className="text-[10px] text-slate-500">{step.tool || "execute"}</span>
            </div>
          ),
        },
        style: {
          background: "#fff",
          border: `2px solid ${color}`,
          borderRadius: 12,
          padding: 4,
          fontSize: 12,
          boxShadow: isParallel
            ? `0 0 0 2px #fbbf24, 0 2px 8px rgba(0,0,0,0.08)`
            : `0 2px 8px rgba(0,0,0,0.06)`,
        },
      });

      if (i > 0 && !isParallel) {
        const deps = step.depends_on || [];
        if (deps.length > 0) {
          deps.forEach((dep) => {
            const depIdx = sorted.findIndex((s) => s.agent === dep);
            if (depIdx >= 0) {
              e.push({
                id: `e-${depIdx}-${i}`,
                source: `step-${depIdx}`,
                target: `step-${i}`,
                markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
                style: { stroke: "#94a3b8", strokeWidth: 2 },
                animated: true,
              });
            }
          });
        } else {
          e.push({
            id: `e-${i - 1}-${i}`,
            source: `step-${i - 1}`,
            target: `step-${i}`,
            markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
            style: { stroke: "#94a3b8", strokeWidth: 2 },
            animated: true,
          });
        }
      }
    });

    return { nodes: n, edges: e };
  }, [plan]);

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400 text-sm">
        No pipeline steps to visualize
      </div>
    );
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      fitView
      fitViewOptions={{ padding: 0.3 }}
      nodesDraggable={true}
      panOnDrag={true}
      zoomOnScroll={false}
      className="rounded-lg"
    >
      <Background color="#f1f5f9" gap={16} />
      <Controls showInteractive={false} className="!rounded-lg !border-slate-200" />
    </ReactFlow>
  );
}
