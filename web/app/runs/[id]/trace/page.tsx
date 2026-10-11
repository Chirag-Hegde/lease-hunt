"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { API_URL } from "@/lib/api-client";
import { cn, formatUSD } from "@/lib/utils";

type Span = {
  id: string;
  name: string;
  kind: "agent" | "tool" | "llm";
  agent: string | null;
  listing_id: string | null;
  start: string;
  end: string;
  duration_ms: number;
  status: string | null;
  model: string | null;
  prompt_version: string | null;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  cached: boolean;
};

type Trace = {
  run_id: string;
  started_at: string;
  finished_at: string | null;
  spans: Span[];
  total_cost_usd: number;
  total_tokens: number;
};

const KIND_COLOR: Record<Span["kind"], string> = {
  agent: "bg-primary",
  tool: "bg-severity-info",
  llm: "bg-accent",
};

export default function TraceViewerPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;
  const [kindFilter, setKindFilter] = useState<Span["kind"] | null>(null);

  const { data } = useQuery({
    queryKey: ["trace", runId],
    queryFn: async () => {
      const resp = await fetch(`${API_URL}/api/runs/${runId}/trace`);
      if (!resp.ok) throw new Error(await resp.text());
      return (await resp.json()) as Trace;
    },
  });

  if (!data) {
    return <div className="container py-8"><div className="skeleton h-96" /></div>;
  }

  const t0 = new Date(data.started_at).getTime();
  const tEnd = data.finished_at
    ? new Date(data.finished_at).getTime()
    : Math.max(...data.spans.map((s) => new Date(s.end).getTime()), t0 + 1000);
  const total = Math.max(tEnd - t0, 1);
  const spans = data.spans.filter((s) => kindFilter == null || s.kind === kindFilter);

  return (
    <div className="container max-w-6xl py-8">
      <Link href={`/runs/${runId}`} className="text-xs text-muted-foreground hover:text-foreground">
        ← Mission Control
      </Link>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl">Agent Trace</h1>
          <p className="text-sm text-muted-foreground">
            {data.spans.length} spans · {(total / 1000).toFixed(1)}s ·{" "}
            {data.total_tokens.toLocaleString()} tokens · {formatUSD(data.total_cost_usd, 4)}
          </p>
        </div>
        <div className="flex gap-1.5">
          {(["agent", "tool", "llm"] as const).map((kind) => (
            <button
              key={kind}
              type="button"
              aria-pressed={kindFilter === kind}
              onClick={() => setKindFilter(kindFilter === kind ? null : kind)}
              className={cn(
                "flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs",
                kindFilter === kind ? "border-primary bg-primary/10" : "text-muted-foreground",
              )}
            >
              <span className={cn("h-2 w-2 rounded-full", KIND_COLOR[kind])} /> {kind}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 space-y-px overflow-x-auto rounded-lg border bg-card p-4 shadow-soft">
        {spans.map((span) => {
          const left = ((new Date(span.start).getTime() - t0) / total) * 100;
          const width = Math.max(
            ((new Date(span.end).getTime() - new Date(span.start).getTime()) / total) * 100,
            0.4,
          );
          return (
            <div key={span.id} className="group flex items-center gap-2 py-0.5 text-xs">
              <div className="w-56 shrink-0 truncate">
                <span className="font-medium">{span.name}</span>
                {span.listing_id && (
                  <span className="ml-1 text-muted-foreground">· {span.listing_id.slice(0, 8)}</span>
                )}
              </div>
              <div className="relative h-5 flex-1 rounded bg-muted/50">
                <div
                  className={cn("absolute top-1 h-3 rounded-sm", KIND_COLOR[span.kind])}
                  style={{ left: `${left}%`, width: `${width}%` }}
                  title={`${span.name}: ${span.duration_ms}ms`}
                />
              </div>
              <div className="w-64 shrink-0 text-right tabular-nums text-muted-foreground">
                {span.duration_ms}ms
                {span.kind === "llm" && (
                  <>
                    {" · "}
                    {span.tokens_in + span.tokens_out} tok · {formatUSD(span.cost_usd, 5)}
                    {span.cached && (
                      <Badge variant="verified" className="ml-1">
                        cache
                      </Badge>
                    )}
                    <span className="ml-1 text-[10px]">
                      {span.model} v{span.prompt_version}
                    </span>
                  </>
                )}
                {span.kind === "agent" && span.status && (
                  <Badge
                    variant={span.status === "ok" ? "verified" : span.status === "error" ? "high" : "caution"}
                    className="ml-1"
                  >
                    {span.status}
                  </Badge>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        Every span is also recorded to the llm_calls table with model, prompt version, tokens,
        cost, and latency — the same data exported to OpenTelemetry/Langfuse when configured.
      </p>
    </div>
  );
}
