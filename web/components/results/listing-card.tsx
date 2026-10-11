"use client";

import { AlertTriangle, Clock } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ScoreRing } from "@/components/results/score-ring";
import { Badge } from "@/components/ui/badge";
import type { ListingWithResults } from "@/lib/api-client";
import { cn, formatMinutes, formatUSD } from "@/lib/utils";

type CommuteData = {
  per_place?: Array<{ place_label: string; best_mode: string; best_peak_minutes: number }>;
};
type PriceData = { total_monthly_cost?: number };

export function ListingCard({
  entry,
  score,
  pros,
  redFlag,
  verified,
  selected,
  onHover,
}: {
  entry: ListingWithResults;
  score: number;
  pros: string[];
  redFlag: string | null;
  verified: boolean;
  selected: boolean;
  onHover?: () => void;
}) {
  const listing = entry.listing;
  const [imgFailed, setImgFailed] = useState(false);
  const results = (entry.results ?? {}) as Record<string, { data?: unknown } | undefined>;
  const commute = (results.commute?.data ?? null) as CommuteData | null;
  const price = (results.price?.data ?? null) as PriceData | null;
  const photo = listing.photos?.[0];

  return (
    <div
      onMouseEnter={onHover}
      className={cn(
        "flex gap-4 rounded-lg border bg-card p-4 shadow-soft transition-shadow hover:shadow-lifted",
        selected && "ring-2 ring-accent",
      )}
    >
      <div className="hidden h-28 w-36 shrink-0 overflow-hidden rounded-md sm:block">
        {photo && !imgFailed ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={photo}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div
            aria-hidden
            className="h-full w-full bg-gradient-to-br from-primary/20 via-secondary to-accent/20"
          />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <Link
              href={`/listings/${listing.id}`}
              className="block truncate font-medium hover:text-primary"
            >
              {listing.address}
            </Link>
            <p className="mt-0.5 text-sm text-muted-foreground">
              <span className="font-serif text-lg text-foreground">{formatUSD(listing.rent)}</span>
              /mo
              {price?.total_monthly_cost != null && (
                <span> · true cost {formatUSD(price.total_monthly_cost)}</span>
              )}{" "}
              · {listing.beds === 0 ? "Studio" : `${listing.beds}bd`}/{listing.baths}ba
              {listing.sqft ? ` · ${listing.sqft} sqft` : ""}
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-center gap-1">
            <ScoreRing score={score} label="Overall score" />
            {verified && <Badge variant="verified">✓ Critic</Badge>}
          </div>
        </div>

        {pros.length > 0 && (
          <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
            {pros.map((pro) => (
              <li key={pro} className="before:mr-1 before:text-primary before:content-['✓']">
                {pro}
              </li>
            ))}
          </ul>
        )}

        {redFlag && (
          <p className="mt-1.5 flex items-center gap-1 text-xs text-severity-high">
            <AlertTriangle className="h-3 w-3 shrink-0" /> {redFlag}
          </p>
        )}

        {commute?.per_place && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {commute.per_place.map((place) => (
              <span
                key={place.place_label}
                className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground"
              >
                <Clock className="h-2.5 w-2.5" />
                {place.place_label}: {formatMinutes(place.best_peak_minutes)} ({place.best_mode})
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
