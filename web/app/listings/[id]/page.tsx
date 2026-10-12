"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, FileText, PenLine } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { CommuteSection, type CommuteData } from "@/components/listing/commute-section";
import {
  ReputationSection,
  type Evidence,
  type ReviewInsightsData,
} from "@/components/listing/reputation-section";
import { ValueSection, type PriceData } from "@/components/listing/value-section";
import { ScoreRing } from "@/components/results/score-ring";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { cn, formatUSD } from "@/lib/utils";

type AgentEnvelope = {
  status: string;
  reason?: string | null;
  data?: unknown;
  evidence?: Evidence[];
  confidence?: number;
};

function Section({
  title,
  score,
  status,
  reason,
  defaultOpen,
  children,
}: {
  title: string;
  score?: number | null;
  status?: string;
  reason?: string | null;
  defaultOpen?: boolean;
  children?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  const unavailable = status && status !== "ok" && status !== "partial";
  return (
    <section className="rounded-lg border bg-card shadow-soft">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 p-4 text-left"
      >
        <div className="flex items-center gap-3">
          {score != null ? (
            <ScoreRing score={score} size={44} label={title} />
          ) : (
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-muted text-xs text-muted-foreground">
              —
            </span>
          )}
          <div>
            <h3 className="font-serif text-lg">{title}</h3>
            {status === "partial" && <Badge variant="caution">partial</Badge>}
            {unavailable && (
              <p className="text-xs text-muted-foreground">{reason ?? "unavailable"}</p>
            )}
          </div>
        </div>
        <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
      </button>
      {open && !unavailable && <div className="border-t p-4">{children}</div>}
      {open && unavailable && (
        <div className="border-t p-4 text-sm text-muted-foreground">
          {reason ?? "This analysis isn't available for this listing."}
        </div>
      )}
    </section>
  );
}

export default function ListingDetailPage() {
  const params = useParams<{ id: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["listing", params.id],
    queryFn: () => api.getListing(params.id),
  });
  const [heroFailed, setHeroFailed] = useState(false);

  if (isLoading) {
    return (
      <div className="container space-y-4 py-8">
        <div className="skeleton h-64" />
        <div className="skeleton h-10 w-1/2" />
        <div className="skeleton h-40" />
      </div>
    );
  }
  if (!data) {
    return <div className="container py-16 text-center text-muted-foreground">Listing not found.</div>;
  }

  const listing = data.listing;
  const results = (data.results ?? {}) as Record<string, AgentEnvelope | undefined>;
  const commute = results.commute;
  const review = results.review;
  const price = results.price;
  const commuteData = commute?.data as CommuteData | undefined;
  const reviewData = review?.data as ReviewInsightsData | undefined;
  const priceData = price?.data as PriceData | undefined;

  return (
    <div className="container max-w-5xl py-8">
      {/* Gallery — only photos the listing source actually provides. */}
      {(listing.photos ?? []).length > 0 && !heroFailed && (
        <div className="grid h-72 grid-cols-3 gap-2 overflow-hidden rounded-lg">
          {(listing.photos ?? []).slice(0, 3).map((photo, i) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={i}
              src={photo}
              alt={`Listing photo ${i + 1}`}
              onError={() => setHeroFailed(true)}
              className={cn("h-full w-full object-cover", i === 0 && "col-span-2 row-span-2")}
            />
          ))}
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl">{listing.address}</h1>
          <p className="mt-1 text-muted-foreground">
            <span className="font-serif text-2xl text-foreground">{formatUSD(listing.rent)}</span>
            /mo
            {priceData && <span> · true cost {formatUSD(priceData.total_monthly_cost)}/mo</span>}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge variant="secondary">
              {listing.beds === 0 ? "Studio" : `${listing.beds} bed`} · {listing.baths} bath
            </Badge>
            {listing.sqft && <Badge variant="secondary">{listing.sqft} sqft</Badge>}
            {listing.available_date && (
              <Badge variant="secondary">available {listing.available_date}</Badge>
            )}
            {listing.building_name && <Badge variant="outline">{listing.building_name}</Badge>}
            {listing.landlord && <Badge variant="outline">{listing.landlord}</Badge>}
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            {(listing.amenities ?? []).map((amenity) => (
              <span key={amenity} className="rounded-full bg-muted px-2 py-0.5 text-xs">
                {amenity}
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <Link href={`/leases/upload?listing=${listing.id}`} className={buttonVariants({})}>
            <FileText className="h-4 w-4" /> Upload lease for this unit
          </Link>
          <Link
            href={`/listings/${listing.id}/negotiate`}
            className={buttonVariants({ variant: "outline" })}
          >
            <PenLine className="h-4 w-4" /> Draft negotiation
          </Link>
        </div>
      </div>

      <div className="mt-8 space-y-4">
        <Section
          title="Commute"
          score={commuteData?.overall_score}
          status={commute?.status}
          reason={commute?.reason}
          defaultOpen
        >
          {commuteData && <CommuteSection data={commuteData} />}
        </Section>

        <Section
          title="Reputation"
          score={reviewData?.management_score}
          status={review?.status}
          reason={review?.reason}
          defaultOpen
        >
          {reviewData && (
            <ReputationSection data={reviewData} evidence={review?.evidence ?? []} />
          )}
        </Section>

        <Section
          title="Value"
          score={priceData ? Math.round(100 - priceData.percentile) : null}
          status={price?.status}
          reason={price?.reason}
          defaultOpen
        >
          {priceData && <ValueSection data={priceData} rent={listing.rent} />}
        </Section>
      </div>

      {!commute && !review && !price && (
        <p className="mt-6 rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          No agent analysis yet — this listing hasn't been part of a run.{" "}
          <Link href="/new" className="text-primary underline">
            Start a search
          </Link>{" "}
          that includes it.
        </p>
      )}
    </div>
  );
}
