"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { formatUSD } from "@/lib/utils";

export function InterruptModal({
  interrupt,
  onDecision,
  busy,
}: {
  interrupt: Record<string, unknown>;
  onDecision: (approve: boolean, maxListings?: number) => void;
  busy: boolean;
}) {
  const listingCount = (interrupt.listing_count as number) ?? 0;
  const defaultTopN = (interrupt.default_top_n as number) ?? 8;
  const estCost = (interrupt.estimated_cost_usd as number) ?? 0;
  const [count, setCount] = useState(listingCount);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Deep analysis approval"
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/30 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-md animate-fade-up rounded-lg border bg-card p-6 shadow-lifted">
        <h2 className="font-serif text-xl">Deep-analyze {listingCount} listings?</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {String(interrupt.question ?? "")} Estimated cost: {formatUSD(estCost, 3)}.
        </p>
        <label className="mt-4 block text-sm">
          Listings to analyze: <span className="font-medium tabular-nums">{count}</span>
          <input
            type="range"
            min={1}
            max={listingCount}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="mt-1 w-full accent-[hsl(var(--primary))]"
          />
        </label>
        <div className="mt-6 flex justify-end gap-2">
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => onDecision(false, defaultTopN)}
          >
            Just top {defaultTopN}
          </Button>
          <Button disabled={busy} onClick={() => onDecision(true, count)}>
            Analyze {count}
          </Button>
        </div>
      </div>
    </div>
  );
}
