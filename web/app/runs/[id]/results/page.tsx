"use client";

import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Map as MapIcon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { ListingCard } from "@/components/results/listing-card";
import { ResultsMap, type IsochroneBand, type MapPin } from "@/components/results/results-map";
import { WeightSliders } from "@/components/results/weight-sliders";
import { api, type ListingWithResults } from "@/lib/api-client";
import { DEFAULT_WEIGHTS, finalScore, type Scores, type Weights } from "@/lib/ranking";
import { cn } from "@/lib/utils";

type RankedEntry = {
  listing_id: string;
  scores: Scores;
  top_pros: string[];
  top_red_flag: string | null;
  critic_verified: boolean;
};

export default function ResultsExplorerPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;
  const [weights, setWeights] = useState<Weights>({ ...DEFAULT_WEIGHTS });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showIsochrone, setShowIsochrone] = useState(true);
  const [maxPrice, setMaxPrice] = useState<number | null>(null);
  const [minBeds, setMinBeds] = useState(0);
  const [maxCommute, setMaxCommute] = useState<number | null>(null);
  const [hideHighRisk, setHideHighRisk] = useState(false);

  const { data: run, isLoading } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
  });

  const report = run?.report as
    | {
        ranked: RankedEntry[];
        formula: string;
        isochrones?: IsochroneBand[];
        relax_suggestion?: string | null;
      }
    | null
    | undefined;

  const reranked = useMemo(() => {
    if (!report || !run) return [];
    const listingMap = (run.listings ?? {}) as Record<string, ListingWithResults>;
    return report.ranked
      .map((entry) => ({
        ...entry,
        score: finalScore(entry.scores, weights),
        detail: listingMap[entry.listing_id],
      }))
      .filter((entry) => entry.detail != null)
      .filter((entry) => {
        const listing = entry.detail!.listing;
        if (maxPrice != null && listing.rent > maxPrice) return false;
        if ((listing.beds ?? 0) < minBeds) return false;
        if (hideHighRisk && entry.top_red_flag) return false;
        if (maxCommute != null) {
          const results = (entry.detail!.results ?? {}) as Record<
            string,
            { data?: { per_place?: Array<{ best_peak_minutes: number }> } } | undefined
          >;
          const commute = results.commute?.data;
          const worst = Math.max(
            0,
            ...(commute?.per_place?.map((p) => p.best_peak_minutes) ?? [0]),
          );
          if (worst > maxCommute) return false;
        }
        return true;
      })
      .sort((a, b) => b.score - a.score);
  }, [report, run, weights, maxPrice, minBeds, maxCommute, hideHighRisk]);

  const pins: MapPin[] = useMemo(
    () =>
      reranked
        .filter((e) => e.detail!.listing.lat != null)
        .map((e) => ({
          listingId: e.listing_id,
          lat: e.detail!.listing.lat!,
          lng: e.detail!.listing.lng!,
          rent: e.detail!.listing.rent,
          score: e.score,
        })),
    [reranked],
  );

  if (isLoading) {
    return (
      <div className="container space-y-4 py-8">
        <div className="skeleton h-10 w-64" />
        <div className="skeleton h-[420px]" />
      </div>
    );
  }

  if (!run || run.status !== "finished" || !report) {
    return (
      <div className="container py-16 text-center">
        <h1 className="text-2xl">Results not ready</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          This run is {run?.status ?? "unknown"}.{" "}
          <Link href={`/runs/${runId}`} className="text-primary underline">
            Watch it in Mission Control
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="container py-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            href={`/runs/${runId}`}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> Mission Control
          </Link>
          <h1 className="text-3xl">Results Explorer</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <label className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Max rent</span>
            <input
              type="number"
              step={100}
              placeholder="any"
              value={maxPrice ?? ""}
              onChange={(e) => setMaxPrice(e.target.value ? Number(e.target.value) : null)}
              className="w-24 rounded-md border bg-background p-1.5 text-sm"
            />
          </label>
          <label className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Beds ≥</span>
            <select
              value={minBeds}
              onChange={(e) => setMinBeds(Number(e.target.value))}
              className="rounded-md border bg-background p-1.5 text-sm"
            >
              {[0, 1, 2, 3].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Max commute</span>
            <input
              type="number"
              step={5}
              placeholder="any"
              value={maxCommute ?? ""}
              onChange={(e) => setMaxCommute(e.target.value ? Number(e.target.value) : null)}
              className="w-20 rounded-md border bg-background p-1.5 text-sm"
            />
          </label>
          <label className="flex cursor-pointer items-center gap-1.5">
            <input
              type="checkbox"
              checked={hideHighRisk}
              onChange={(e) => setHideHighRisk(e.target.checked)}
              className="accent-[hsl(var(--primary))]"
            />
            <span className="text-muted-foreground">Hide red-flagged</span>
          </label>
          <button
            type="button"
            onClick={() => setShowIsochrone(!showIsochrone)}
            aria-pressed={showIsochrone}
            className={cn(
              "flex items-center gap-1 rounded-md border px-2 py-1.5 text-sm",
              showIsochrone
                ? "border-primary bg-primary/10 text-primary"
                : "text-muted-foreground",
            )}
          >
            <MapIcon className="h-3.5 w-3.5" />
            {report.isochrones?.[0]
              ? `≤${report.isochrones[0].minutes} min zone`
              : "Isochrone"}
          </button>
        </div>
      </div>

      {report.relax_suggestion && (
        <p className="mb-4 rounded-lg border border-severity-caution/40 bg-severity-caution/10 p-3 text-sm">
          {report.relax_suggestion}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_minmax(380px,46%)]">
        <div className="lg:sticky lg:top-20 lg:h-[calc(100vh-7rem)]">
          <ResultsMap
            pins={pins}
            isochrones={report.isochrones ?? []}
            showIsochrone={showIsochrone}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>

        <div className="space-y-4">
          <div className="sticky top-16 z-10">
            <WeightSliders weights={weights} onChange={setWeights} formula={report.formula} />
          </div>
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {reranked.length} listings, ranked by your weights
          </p>
          <AnimatePresence initial={false}>
            {reranked.map((entry) => (
              <motion.div
                key={entry.listing_id}
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
              >
                <ListingCard
                  entry={entry.detail!}
                  score={entry.score}
                  pros={entry.top_pros}
                  redFlag={entry.top_red_flag}
                  verified={entry.critic_verified}
                  selected={selectedId === entry.listing_id}
                  onHover={() => setSelectedId(entry.listing_id)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
