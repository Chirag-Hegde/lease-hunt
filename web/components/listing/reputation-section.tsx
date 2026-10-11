"use client";

import { AlertTriangle, ChevronDown, ExternalLink, TrendingDown, TrendingUp } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type Evidence = {
  id: string;
  source_type: string;
  source_url: string | null;
  excerpt: string | null;
};

export type ThemeInsight = {
  theme: string;
  frequency: number;
  sentiment: number;
  trend: "improving" | "stable" | "worsening";
  recent_spike: boolean;
  evidence_ids: string[];
};

export type ReviewInsightsData = {
  review_count: number;
  themes: ThemeInsight[];
  management_score: number;
  red_flags: string[];
  fake_review_suspicion: boolean;
  fake_review_note: string | null;
};

function sentimentColor(sentiment: number): string {
  if (sentiment < -0.35) return "bg-severity-high";
  if (sentiment < 0) return "bg-severity-caution";
  return "bg-primary";
}

export function ReputationSection({
  data,
  evidence,
}: {
  data: ReviewInsightsData;
  evidence: Evidence[];
}) {
  const [openTheme, setOpenTheme] = useState<string | null>(null);
  const evidenceById = new Map(evidence.map((e) => [e.id, e]));
  const maxFreq = Math.max(1, ...data.themes.map((t) => t.frequency));

  return (
    <div className="space-y-4">
      {data.fake_review_suspicion && data.fake_review_note && (
        <p className="flex items-start gap-2 rounded-md border border-severity-caution/40 bg-severity-caution/10 p-3 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-severity-caution" />
          {data.fake_review_note}
        </p>
      )}

      {data.red_flags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {data.red_flags.map((flag) => (
            <Badge key={flag} variant="high">
              {flag}
            </Badge>
          ))}
        </div>
      )}

      <div className="space-y-2">
        {data.themes.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No recurring complaint themes found across {data.review_count} reviews — a good sign.
          </p>
        )}
        {data.themes.map((theme) => {
          const themeEvidence = theme.evidence_ids
            .map((id) => evidenceById.get(id))
            .filter((e): e is Evidence => e != null);
          const open = openTheme === theme.theme;
          return (
            <div key={theme.theme} className="rounded-md border">
              <button
                type="button"
                onClick={() => setOpenTheme(open ? null : theme.theme)}
                aria-expanded={open}
                className="flex w-full items-center gap-3 p-3 text-left"
              >
                <span className="w-28 shrink-0 text-sm capitalize">
                  {theme.theme.replace("_", " ")}
                </span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                  <span
                    className={cn("block h-full rounded-full", sentimentColor(theme.sentiment))}
                    style={{ width: `${(theme.frequency / maxFreq) * 100}%` }}
                  />
                </span>
                <span className="w-16 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                  ×{theme.frequency}
                </span>
                <span className="flex w-24 shrink-0 items-center justify-end gap-1 text-xs text-muted-foreground">
                  {theme.trend === "worsening" ? (
                    <TrendingUp className="h-3 w-3 text-severity-high" />
                  ) : theme.trend === "improving" ? (
                    <TrendingDown className="h-3 w-3 text-primary" />
                  ) : null}
                  {theme.trend}
                </span>
                <ChevronDown
                  className={cn("h-4 w-4 shrink-0 transition-transform", open && "rotate-180")}
                />
              </button>
              {open && (
                <div className="space-y-2 border-t bg-muted/30 p-3">
                  {theme.recent_spike && (
                    <Badge variant="caution">spiked in the last 6 months</Badge>
                  )}
                  {themeEvidence.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No excerpts available.</p>
                  ) : (
                    themeEvidence.map((item) => (
                      <blockquote
                        key={item.id}
                        className="border-l-2 border-primary/40 pl-3 text-xs text-muted-foreground"
                      >
                        “{item.excerpt}”
                        {item.source_url && (
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="ml-1 inline-flex items-center gap-0.5 text-primary hover:underline"
                          >
                            source <ExternalLink className="h-2.5 w-2.5" />
                          </a>
                        )}
                      </blockquote>
                    ))
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <p className="text-xs text-muted-foreground">
        Based on {data.review_count} reviews & community posts. Short excerpts shown with links —
        read the sources before deciding.
      </p>
    </div>
  );
}
