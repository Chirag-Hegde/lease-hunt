"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, FileText } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { api, API_URL } from "@/lib/api-client";
import type { LeaseResponse } from "@/lib/lease-types";
import { formatUSD } from "@/lib/utils";

export default function SavedPage() {
  const { data: runs } = useQuery({ queryKey: ["runs"], queryFn: () => api.listRuns() });
  const { data: leases } = useQuery({
    queryKey: ["leases"],
    queryFn: async () => {
      const resp = await fetch(`${API_URL}/api/leases`);
      if (!resp.ok) throw new Error(await resp.text());
      return (await resp.json()) as LeaseResponse[];
    },
  });

  return (
    <div className="container max-w-4xl py-10">
      <h1 className="text-3xl">Saved & history</h1>

      <section className="mt-8">
        <h2 className="flex items-center gap-2 text-lg">
          <Activity className="h-4 w-4 text-primary" /> Search runs
        </h2>
        <div className="mt-3 space-y-2">
          {(runs ?? []).map((run) => (
            <Link
              key={run.id}
              href={run.status === "finished" ? `/runs/${run.id}/results` : `/runs/${run.id}`}
              className="flex items-center justify-between rounded-lg border bg-card p-3 text-sm shadow-soft transition-shadow hover:shadow-lifted"
            >
              <div>
                <span className="font-mono text-xs text-muted-foreground">
                  {run.id.slice(0, 8)}
                </span>
                <span className="ml-2">{new Date(run.started_at).toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs tabular-nums text-muted-foreground">
                  {formatUSD(run.cost_usd, 4)} · {(run.tokens_in + run.tokens_out).toLocaleString()} tok
                </span>
                <Badge
                  variant={
                    run.status === "finished"
                      ? "verified"
                      : run.status === "failed"
                        ? "high"
                        : "caution"
                  }
                >
                  {run.status}
                </Badge>
              </div>
            </Link>
          ))}
          {runs?.length === 0 && (
            <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              No runs yet.{" "}
              <Link href="/new" className="text-primary underline">
                Start a search
              </Link>
            </p>
          )}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="flex items-center gap-2 text-lg">
          <FileText className="h-4 w-4 text-primary" /> Analyzed leases
        </h2>
        <div className="mt-3 space-y-2">
          {(leases ?? []).map((lease) => (
            <Link
              key={lease.id}
              href={`/leases/${lease.id}`}
              className="flex items-center justify-between rounded-lg border bg-card p-3 text-sm shadow-soft transition-shadow hover:shadow-lifted"
            >
              <span>{lease.filename}</span>
              <div className="flex items-center gap-2">
                {lease.risk_score != null && (
                  <Badge
                    variant={
                      lease.risk_score >= 50 ? "high" : lease.risk_score >= 20 ? "caution" : "verified"
                    }
                  >
                    risk {lease.risk_score}
                  </Badge>
                )}
                <span className="text-xs text-muted-foreground">
                  {new Date(lease.created_at).toLocaleDateString()}
                </span>
              </div>
            </Link>
          ))}
          {leases?.length === 0 && (
            <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              No leases analyzed yet.{" "}
              <Link href="/leases/upload" className="text-primary underline">
                Upload one
              </Link>
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
