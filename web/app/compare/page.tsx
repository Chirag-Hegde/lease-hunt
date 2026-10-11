"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

import { API_URL, type ListingWithResults } from "@/lib/api-client";
import { cn, formatMinutes, formatUSD } from "@/lib/utils";

const SERIES_COLORS = ["#0F766E", "#D97706", "#64748B", "#E11D48"];

type Entry = ListingWithResults & { results: Record<string, { status?: string; data?: any }> };

function dims(entry: Entry) {
  const commute = entry.results.commute?.data?.overall_score ?? null;
  const value =
    entry.results.price?.data?.percentile != null
      ? 100 - entry.results.price.data.percentile
      : null;
  const reputation = entry.results.review?.data?.management_score ?? null;
  const leaseSafety =
    entry.results.lease?.data?.risk_score != null
      ? 100 - entry.results.lease.data.risk_score
      : null;
  return { commute, value, reputation, leaseSafety };
}

function CompareInner() {
  const searchParams = useSearchParams();
  const ids = searchParams.get("ids") ?? "";

  const { data, isLoading, error } = useQuery({
    queryKey: ["compare", ids],
    queryFn: async () => {
      const resp = await fetch(`${API_URL}/api/compare?ids=${ids}`);
      if (!resp.ok) throw new Error(await resp.text());
      return (await resp.json()) as { listings: Entry[] };
    },
    enabled: ids.split(",").filter(Boolean).length >= 2,
  });

  const listings = data?.listings ?? [];

  if (ids.split(",").filter(Boolean).length < 2) {
    return (
      <div className="container py-16 text-center text-muted-foreground">
        Pick 2–4 listings to compare (select them in the Results Explorer).
      </div>
    );
  }
  if (isLoading) return <div className="container py-8"><div className="skeleton h-96" /></div>;
  if (error || listings.length < 2) {
    return <div className="container py-16 text-center text-muted-foreground">Could not load listings.</div>;
  }

  const radarData = (
    [
      ["Commute", "commute"],
      ["Value", "value"],
      ["Reputation", "reputation"],
      ["Lease safety", "leaseSafety"],
    ] as const
  ).map(([label, key]) => {
    const row: Record<string, string | number> = { dimension: label };
    listings.forEach((entry, i) => {
      const value = dims(entry)[key];
      if (value != null) row[`l${i}`] = Math.round(value);
    });
    return row;
  });

  const rows: Array<{
    label: string;
    value: (e: Entry) => number | null;
    format: (v: number) => string;
    higherIsBetter: boolean;
  }> = [
    { label: "Rent", value: (e) => e.listing.rent, format: (v) => `${formatUSD(v)}/mo`, higherIsBetter: false },
    {
      label: "True monthly cost",
      value: (e) => e.results.price?.data?.total_monthly_cost ?? null,
      format: (v) => `${formatUSD(v)}/mo`,
      higherIsBetter: false,
    },
    { label: "Square feet", value: (e) => e.listing.sqft ?? null, format: (v) => `${v}`, higherIsBetter: true },
    {
      label: "Worst commute (peak)",
      value: (e) => {
        const places = e.results.commute?.data?.per_place as
          | Array<{ best_peak_minutes: number }>
          | undefined;
        return places?.length ? Math.max(...places.map((p) => p.best_peak_minutes)) : null;
      },
      format: (v) => formatMinutes(v),
      higherIsBetter: false,
    },
    {
      label: "Commute score",
      value: (e) => dims(e).commute,
      format: (v) => `${Math.round(v)}/100`,
      higherIsBetter: true,
    },
    {
      label: "Reputation score",
      value: (e) => dims(e).reputation,
      format: (v) => `${Math.round(v)}/100`,
      higherIsBetter: true,
    },
    {
      label: "Rent percentile vs comps",
      value: (e) => e.results.price?.data?.percentile ?? null,
      format: (v) => `${Math.round(v)}th`,
      higherIsBetter: false,
    },
    {
      label: "Lease risk",
      value: (e) => e.results.lease?.data?.risk_score ?? null,
      format: (v) => `${Math.round(v)}/100`,
      higherIsBetter: false,
    },
  ];

  const bestIndex = (row: (typeof rows)[number]) => {
    const values = listings.map((entry) => row.value(entry));
    let best = -1;
    values.forEach((v, i) => {
      if (v == null) return;
      if (best === -1) best = i;
      else {
        const current = values[best]!;
        if (row.higherIsBetter ? v > current : v < current) best = i;
      }
    });
    return best;
  };

  return (
    <div className="container py-8">
      <h1 className="text-3xl">Compare</h1>
      <div className="mt-6 h-80 w-full">
        <ResponsiveContainer>
          <RadarChart data={radarData}>
            <PolarGrid stroke="hsl(var(--border))" />
            <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 12 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            {listings.map((entry, i) => (
              <Radar
                key={entry.listing.id}
                name={entry.listing.address.split(",")[0]}
                dataKey={`l${i}`}
                stroke={SERIES_COLORS[i]}
                fill={SERIES_COLORS[i]}
                fillOpacity={0.12}
              />
            ))}
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-8 overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b">
              <th className="py-2 pr-4 text-left font-normal text-muted-foreground">Dimension</th>
              {listings.map((entry) => (
                <th key={entry.listing.id} className="px-3 py-2 text-left">
                  <a href={`/listings/${entry.listing.id}`} className="hover:text-primary">
                    {entry.listing.address.split(",")[0]}
                  </a>
                  <p className="text-xs font-normal text-muted-foreground">
                    {entry.listing.beds === 0 ? "Studio" : `${entry.listing.beds}bd`}/
                    {entry.listing.baths}ba · {entry.listing.building_name ?? entry.listing.city}
                  </p>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const best = bestIndex(row);
              return (
                <tr key={row.label} className="border-b border-border/60">
                  <td className="py-2.5 pr-4 text-muted-foreground">{row.label}</td>
                  {listings.map((entry, i) => {
                    const value = row.value(entry);
                    return (
                      <td
                        key={entry.listing.id}
                        className={cn(
                          "px-3 py-2.5 tabular-nums",
                          i === best && value != null && "font-semibold text-primary",
                        )}
                      >
                        {value != null ? row.format(value) : "—"}
                        {i === best && value != null && " ✓"}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense>
      <CompareInner />
    </Suspense>
  );
}
