"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RunEvent } from "@/lib/hooks/use-run-events";

function describe(event: RunEvent): string {
  const p = event.payload;
  switch (event.type) {
    case "tool_called":
      return `tool: ${String(p.tool ?? "?")}${p.provider ? ` (${String(p.provider)})` : ""}`;
    case "agent_started":
      return p.listing_id ? `started for listing ${String(p.listing_id)}` : "started";
    case "agent_finished": {
      const cost = typeof p.cost_usd === "number" ? ` · $${p.cost_usd.toFixed(4)}` : "";
      const reason = p.reason ? ` — ${String(p.reason)}` : "";
      return `${String(p.status)} in ${String(p.latency_ms)}ms${cost}${reason}`;
    }
    case "partial_result":
      return "partial result streamed";
    case "critic_rejected":
      return `rejected: ${String(p.claim ?? "claim")}`;
    default:
      return event.type.replace(/_/g, " ");
  }
}

export function EventLog({ events, agent }: { events: RunEvent[]; agent: string | null }) {
  const filtered = agent ? events.filter((e) => e.agent === agent) : events;
  return (
    <Card className="max-h-[320px] overflow-hidden">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          {agent ? `${agent} events` : "Event log"}
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            {filtered.length} events
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="overflow-y-auto">
        <ol className="space-y-1.5 text-xs">
          {filtered
            .slice(-80)
            .reverse()
            .map((event) => (
              <li key={event.seq} className="flex gap-2">
                <span className="shrink-0 tabular-nums text-muted-foreground/60">
                  #{event.seq}
                </span>
                <span className="shrink-0 font-medium text-primary/80">{event.agent ?? "run"}</span>
                <span className="text-muted-foreground">{describe(event)}</span>
              </li>
            ))}
        </ol>
      </CardContent>
    </Card>
  );
}
