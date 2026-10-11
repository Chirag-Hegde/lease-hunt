"use client";

import {
  Background,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Loader2 } from "lucide-react";
import { useMemo } from "react";

import { cn, formatUSD } from "@/lib/utils";
import type { AgentStats, AgentStatus } from "@/lib/hooks/use-run-events";

const AGENT_LAYOUT: Array<{ id: string; label: string; x: number; y: number }> = [
  { id: "scout", label: "Scout", x: 0, y: 150 },
  { id: "commute", label: "Commute", x: 190, y: 30 },
  { id: "price", label: "Price", x: 190, y: 150 },
  { id: "review", label: "Review", x: 190, y: 270 },
  { id: "critic", label: "Critic", x: 390, y: 150 },
  { id: "ranker", label: "Ranker", x: 560, y: 150 },
];

const EDGES: Array<[string, string]> = [
  ["scout", "commute"],
  ["scout", "price"],
  ["scout", "review"],
  ["commute", "critic"],
  ["price", "critic"],
  ["review", "critic"],
  ["critic", "ranker"],
];

const STATUS_STYLES: Record<AgentStatus, string> = {
  idle: "border-border bg-card text-muted-foreground",
  running: "border-primary bg-primary/5 text-foreground shadow-lifted",
  done: "border-primary/60 bg-card text-foreground",
  partial: "border-severity-caution bg-severity-caution/10 text-foreground",
  error: "border-severity-high bg-severity-high/10 text-foreground",
  unavailable: "border-dashed border-border bg-muted text-muted-foreground",
};

type AgentNodeData = {
  label: string;
  stats?: AgentStats;
  selected: boolean;
};

function AgentNode({ data }: NodeProps<Node<AgentNodeData>>) {
  const status = data.stats?.status ?? "idle";
  return (
    <div
      className={cn(
        "w-40 cursor-pointer rounded-lg border px-3 py-2 text-left transition-all",
        STATUS_STYLES[status],
        data.selected && "ring-2 ring-ring ring-offset-2 ring-offset-background",
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-border" />
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{data.label}</span>
        {status === "running" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" aria-label="running" />
        ) : (
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              status === "done" && "bg-primary",
              status === "partial" && "bg-severity-caution",
              status === "error" && "bg-severity-high",
              status === "idle" && "bg-border",
              status === "unavailable" && "bg-muted-foreground/40",
            )}
          />
        )}
      </div>
      {data.stats && data.stats.finishedCount + data.stats.runningCount > 0 ? (
        <p className="mt-1 text-[11px] tabular-nums text-muted-foreground">
          {data.stats.tokens.toLocaleString()} tok · {formatUSD(data.stats.costUsd, 4)}
          {data.stats.finishedCount > 1 ? ` · ×${data.stats.finishedCount}` : ""}
        </p>
      ) : (
        <p className="mt-1 text-[11px] text-muted-foreground">waiting</p>
      )}
      <Handle type="source" position={Position.Right} className="!bg-border" />
    </div>
  );
}

const nodeTypes = { agent: AgentNode };

export function AgentGraph({
  agents,
  selectedAgent,
  onSelectAgent,
}: {
  agents: Record<string, AgentStats>;
  selectedAgent: string | null;
  onSelectAgent: (agent: string | null) => void;
}) {
  const nodes: Node<AgentNodeData>[] = useMemo(
    () =>
      AGENT_LAYOUT.map((item) => ({
        id: item.id,
        type: "agent",
        position: { x: item.x, y: item.y },
        data: { label: item.label, stats: agents[item.id], selected: selectedAgent === item.id },
      })),
    [agents, selectedAgent],
  );

  const edges: Edge[] = useMemo(
    () =>
      EDGES.map(([source, target]) => {
        const active =
          agents[target]?.status === "running" ||
          (agents[source]?.status === "running" && source === "scout");
        return {
          id: `${source}-${target}`,
          source,
          target,
          animated: active,
          style: { stroke: active ? "hsl(var(--primary))" : "hsl(var(--border))", strokeWidth: 1.5 },
        };
      }),
    [agents],
  );

  return (
    <div className="h-[380px] rounded-lg border bg-card/50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelectAgent(selectedAgent === node.id ? null : node.id)}
        onPaneClick={() => onSelectAgent(null)}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        zoomOnScroll={false}
        preventScrolling={false}
      >
        <Background gap={24} size={1} />
      </ReactFlow>
    </div>
  );
}
