"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatUSD } from "@/lib/utils";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="font-serif text-lg tabular-nums">{value}</dd>
    </div>
  );
}

export function RunStats({
  status,
  startedAt,
  totalCost,
  totalTokens,
  criticRejections,
  cacheHits,
  cacheMisses,
}: {
  status: string;
  startedAt: string | null;
  totalCost: number;
  totalTokens: number;
  criticRejections: number;
  cacheHits?: number;
  cacheMisses?: number;
}) {
  const [now, setNow] = useState(() => Date.now());
  const live = status === "running" || status === "pending" || status === "interrupted";
  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [live]);

  const elapsed = startedAt ? Math.max(0, (now - new Date(startedAt).getTime()) / 1000) : 0;
  const cacheTotal = (cacheHits ?? 0) + (cacheMisses ?? 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          Run stats
          <Badge
            variant={
              status === "finished"
                ? "verified"
                : status === "failed"
                  ? "high"
                  : status === "interrupted"
                    ? "caution"
                    : "secondary"
            }
          >
            {status}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="space-y-2">
          <Stat label="Elapsed" value={`${elapsed.toFixed(0)}s`} />
          <Stat label="Total cost" value={formatUSD(totalCost, 4)} />
          <Stat label="Tokens" value={totalTokens.toLocaleString()} />
          <Stat
            label="Cache hit rate"
            value={cacheTotal > 0 ? `${Math.round(((cacheHits ?? 0) / cacheTotal) * 100)}%` : "—"}
          />
          <Stat label="Critic rejections" value={String(criticRejections)} />
        </dl>
      </CardContent>
    </Card>
  );
}
