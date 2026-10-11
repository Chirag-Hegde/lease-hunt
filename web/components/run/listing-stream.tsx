"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, Loader2, X } from "lucide-react";
import Link from "next/link";

import { cn, formatUSD } from "@/lib/utils";
import type { AgentStatus, ListingProgress } from "@/lib/hooks/use-run-events";

const BADGE_AGENTS = ["commute", "review", "price", "critic"] as const;

function AgentBadge({ name, status }: { name: string; status?: AgentStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] capitalize",
        !status && "border-dashed text-muted-foreground/60",
        status === "running" && "border-primary/40 text-primary",
        status === "done" && "border-primary/40 bg-primary/10 text-primary",
        (status === "partial" || status === "unavailable") &&
          "border-severity-caution/40 bg-severity-caution/10 text-severity-caution",
        status === "error" && "border-severity-high/40 bg-severity-high/10 text-severity-high",
      )}
    >
      {status === "running" ? (
        <Loader2 className="h-2.5 w-2.5 animate-spin" />
      ) : status === "done" ? (
        <Check className="h-2.5 w-2.5" />
      ) : status === "error" ? (
        <X className="h-2.5 w-2.5" />
      ) : null}
      {name}
    </span>
  );
}

export function ListingStream({
  listings,
  scoutDone,
}: {
  listings: ListingProgress[];
  scoutDone: boolean;
}) {
  if (listings.length === 0) {
    return (
      <div className="space-y-3" aria-live="polite" aria-busy={!scoutDone}>
        {scoutDone ? (
          <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
            No listings matched this brief.
          </p>
        ) : (
          Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton h-20" />)
        )}
      </div>
    );
  }
  return (
    <ul className="space-y-3">
      <AnimatePresence initial={false}>
        {listings.map((listing) => (
          <motion.li
            key={listing.listingId}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="rounded-lg border bg-card p-4 shadow-soft"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <Link
                  href={`/listings/${listing.listingId}`}
                  className="text-sm font-medium hover:text-primary"
                >
                  {listing.address ?? listing.listingId}
                </Link>
                <p className="text-sm text-muted-foreground">
                  {listing.rent != null ? `${formatUSD(listing.rent)}/mo` : ""}
                </p>
              </div>
              {listing.matchScore != null && (
                <span className="rounded-full bg-primary/10 px-2.5 py-1 font-serif text-sm tabular-nums text-primary">
                  {Math.round(listing.matchScore)}
                </span>
              )}
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {BADGE_AGENTS.map((agent) => (
                <AgentBadge key={agent} name={agent} status={listing.agents[agent]} />
              ))}
            </div>
          </motion.li>
        ))}
      </AnimatePresence>
    </ul>
  );
}
