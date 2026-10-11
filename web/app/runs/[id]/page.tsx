"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AgentGraph } from "@/components/run/agent-graph";
import { EventLog } from "@/components/run/event-log";
import { InterruptModal } from "@/components/run/interrupt-modal";
import { ListingStream } from "@/components/run/listing-stream";
import { RunStats } from "@/components/run/run-stats";
import { buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { useRunEvents } from "@/lib/hooks/use-run-events";

export default function MissionControlPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;
  const queryClient = useQueryClient();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [resuming, setResuming] = useState(false);

  const { events, agents, listings, interrupt, totalCost, totalTokens, criticRejections, status } =
    useRunEvents(runId);

  const { data: run } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
    refetchInterval: status === "finished" || status === "failed" ? false : 5000,
  });

  useEffect(() => {
    if (status === "finished") {
      void queryClient.invalidateQueries({ queryKey: ["run", runId] });
    }
  }, [status, runId, queryClient]);

  const scoutDone = agents.scout != null && agents.scout.status !== "running";
  const effectiveStatus = run?.status === "finished" || run?.status === "failed" ? run.status : status;

  const handleDecision = async (approve: boolean, maxListings?: number) => {
    setResuming(true);
    try {
      await api.resumeRun(runId, { approve, max_listings: maxListings ?? null });
    } finally {
      setResuming(false);
    }
  };

  return (
    <div className="container py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl">Mission Control</h1>
          <p className="text-sm text-muted-foreground">
            Run <span className="font-mono">{runId.slice(0, 8)}</span> — agents working on your
            shortlist in real time.
          </p>
        </div>
        {effectiveStatus === "finished" && (
          <Link href={`/runs/${runId}/results`} className={buttonVariants({})}>
            Explore results <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <AgentGraph
            agents={agents}
            selectedAgent={selectedAgent}
            onSelectAgent={setSelectedAgent}
          />
          <div className="grid gap-6 md:grid-cols-2">
            <section aria-label="Listings found">
              <h2 className="mb-3 text-lg">Listings</h2>
              <ListingStream listings={listings} scoutDone={scoutDone} />
            </section>
            <section aria-label="Event log">
              <h2 className="mb-3 text-lg">Activity</h2>
              <EventLog events={events} agent={selectedAgent} />
            </section>
          </div>
        </div>

        <aside className="space-y-4">
          <RunStats
            status={effectiveStatus}
            startedAt={run?.started_at ?? null}
            totalCost={run?.status === "finished" ? run.cost_usd : totalCost}
            totalTokens={
              run?.status === "finished" ? run.tokens_in + run.tokens_out : totalTokens
            }
            criticRejections={criticRejections || (run?.critic_rejections ?? 0)}
            cacheHits={run?.cache_hits}
            cacheMisses={run?.cache_misses}
          />
          {run?.error && (
            <p className="rounded-lg border border-severity-high/40 bg-severity-high/10 p-3 text-sm text-severity-high">
              {run.error}
            </p>
          )}
        </aside>
      </div>

      {interrupt && effectiveStatus === "interrupted" && (
        <InterruptModal interrupt={interrupt} onDecision={handleDecision} busy={resuming} />
      )}
    </div>
  );
}
