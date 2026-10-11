"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "@/lib/api-client";

export type RunEvent = {
  run_id: string;
  seq: number;
  type:
    | "run_started"
    | "agent_started"
    | "tool_called"
    | "partial_result"
    | "agent_finished"
    | "critic_rejected"
    | "interrupt_required"
    | "run_resumed"
    | "budget_exceeded"
    | "run_finished"
    | "run_failed";
  agent: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type AgentStatus = "idle" | "running" | "done" | "partial" | "error" | "unavailable";

export type AgentStats = {
  status: AgentStatus;
  runningCount: number;
  finishedCount: number;
  tokens: number;
  costUsd: number;
  lastReason?: string;
};

export type ListingProgress = {
  listingId: string;
  address?: string;
  rent?: number;
  matchScore?: number;
  agents: Record<string, AgentStatus>;
};

export function useRunEvents(runId: string | null) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [terminal, setTerminal] = useState(false);
  const seenSeq = useRef(new Set<number>());

  useEffect(() => {
    if (!runId) return;
    setEvents([]);
    seenSeq.current = new Set();
    setTerminal(false);
    const source = new EventSource(api.runEventsUrl(runId));
    const handler = (raw: MessageEvent) => {
      try {
        const event = JSON.parse(raw.data as string) as RunEvent;
        if (seenSeq.current.has(event.seq)) return;
        seenSeq.current.add(event.seq);
        setEvents((prev) => [...prev, event]);
        if (event.type === "run_finished" || event.type === "run_failed") {
          setTerminal(true);
          source.close();
        }
      } catch {
        // ignore malformed frames
      }
    };
    const types = [
      "run_started",
      "agent_started",
      "tool_called",
      "partial_result",
      "agent_finished",
      "critic_rejected",
      "interrupt_required",
      "run_resumed",
      "budget_exceeded",
      "run_finished",
      "run_failed",
    ];
    for (const type of types) source.addEventListener(type, handler);
    source.onerror = () => {
      // EventSource auto-reconnects; nothing to do unless terminal.
    };
    return () => source.close();
  }, [runId]);

  const derived = useMemo(() => {
    const agents: Record<string, AgentStats> = {};
    const listings = new Map<string, ListingProgress>();
    let interrupt: Record<string, unknown> | null = null;
    let totalCost = 0;
    let totalTokens = 0;
    let criticRejections = 0;
    let status: "pending" | "running" | "interrupted" | "finished" | "failed" = "pending";

    const ensureAgent = (name: string): AgentStats =>
      (agents[name] ??= { status: "idle", runningCount: 0, finishedCount: 0, tokens: 0, costUsd: 0 });

    for (const event of events) {
      const p = event.payload;
      switch (event.type) {
        case "run_started":
          status = "running";
          break;
        case "run_resumed":
          status = "running";
          interrupt = null;
          break;
        case "agent_started": {
          const stats = ensureAgent(event.agent ?? "?");
          stats.runningCount += 1;
          stats.status = "running";
          const listingId = p.listing_id as string | undefined;
          if (listingId) {
            const entry = listings.get(listingId) ?? { listingId, agents: {} };
            entry.agents[event.agent ?? "?"] = "running";
            listings.set(listingId, entry);
          }
          break;
        }
        case "agent_finished": {
          const stats = ensureAgent(event.agent ?? "?");
          stats.runningCount = Math.max(0, stats.runningCount - 1);
          stats.finishedCount += 1;
          stats.tokens += ((p.tokens_in as number) ?? 0) + ((p.tokens_out as number) ?? 0);
          stats.costUsd += (p.cost_usd as number) ?? 0;
          totalCost += (p.cost_usd as number) ?? 0;
          totalTokens += ((p.tokens_in as number) ?? 0) + ((p.tokens_out as number) ?? 0);
          const resultStatus = p.status as string;
          if (p.reason) stats.lastReason = p.reason as string;
          if (stats.runningCount === 0) {
            stats.status =
              resultStatus === "ok"
                ? "done"
                : resultStatus === "partial"
                  ? "partial"
                  : resultStatus === "unavailable"
                    ? "unavailable"
                    : "error";
          }
          const listingId = p.listing_id as string | undefined;
          if (listingId) {
            const entry = listings.get(listingId) ?? { listingId, agents: {} };
            entry.agents[event.agent ?? "?"] =
              resultStatus === "ok" ? "done" : resultStatus === "partial" ? "partial" : "error";
            listings.set(listingId, entry);
          }
          break;
        }
        case "partial_result": {
          if (event.agent === "scout" && Array.isArray(p.matches)) {
            for (const match of p.matches as Array<Record<string, unknown>>) {
              const listingId = match.listing_id as string;
              const entry = listings.get(listingId) ?? { listingId, agents: {} };
              entry.address = match.address as string;
              entry.rent = match.rent as number;
              entry.matchScore = match.match_score as number;
              listings.set(listingId, entry);
            }
          }
          break;
        }
        case "critic_rejected":
          criticRejections += 1;
          break;
        case "interrupt_required":
          status = "interrupted";
          interrupt = p;
          break;
        case "run_finished":
          status = "finished";
          break;
        case "run_failed":
          status = "failed";
          break;
        default:
          break;
      }
    }
    return {
      agents,
      listings: Array.from(listings.values()),
      interrupt,
      totalCost,
      totalTokens,
      criticRejections,
      status,
    };
  }, [events]);

  return { events, terminal, ...derived };
}
