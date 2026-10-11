"use client";

import { Check, Copy, ExternalLink } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { SEVERITY_LABEL, type LeaseFinding } from "@/lib/lease-types";
import { cn } from "@/lib/utils";

const SEVERITY_VARIANT = { high: "high", caution: "caution", info: "info" } as const;

export function FindingCard({
  finding,
  selected,
  onSelect,
}: {
  finding: LeaseFinding;
  selected: boolean;
  onSelect: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const copyAsk = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!finding.suggested_ask) return;
    await navigator.clipboard.writeText(finding.suggested_ask);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
      className={cn(
        "cursor-pointer rounded-lg border bg-card p-4 text-left shadow-soft transition-all hover:shadow-lifted",
        selected && "ring-2 ring-accent",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge variant={SEVERITY_VARIANT[finding.severity]}>
            {SEVERITY_LABEL[finding.severity]}
          </Badge>
          <span className="text-sm font-medium capitalize">
            {finding.clause_type.replace(/_/g, " ")}
          </span>
        </div>
        <span className="text-xs text-muted-foreground">p.{finding.citation.page}</span>
      </div>

      <p className="mt-2 text-sm">{finding.explanation}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Why it matters:</span>{" "}
        {finding.why_it_matters}
      </p>

      {finding.suggested_ask && (
        <div className="mt-2 flex items-start gap-2 rounded-md bg-muted/60 p-2">
          <p className="flex-1 text-xs">
            <span className="font-medium">What to ask for:</span> {finding.suggested_ask}
          </p>
          <button
            type="button"
            onClick={copyAsk}
            aria-label="Copy suggested ask"
            className="shrink-0 rounded p-1 text-muted-foreground hover:bg-background hover:text-foreground"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-primary" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
      )}

      {finding.jurisdiction_note && (
        <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
          {finding.jurisdiction_note.verified ? (
            <Badge variant="verified" className="mr-1 align-middle">
              CA law
            </Badge>
          ) : (
            <Badge variant="outline" className="mr-1 align-middle">
              worth asking about
            </Badge>
          )}
          {finding.jurisdiction_note.text}
          {finding.jurisdiction_note.source_url && (
            <a
              href={finding.jurisdiction_note.source_url}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="ml-1 inline-flex items-center gap-0.5 text-primary hover:underline"
            >
              official source <ExternalLink className="h-2.5 w-2.5" />
            </a>
          )}
        </p>
      )}

      <div className="mt-2 flex items-center gap-2" aria-label={`Confidence ${Math.round(finding.confidence * 100)}%`}>
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
          confidence
        </span>
        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary"
            style={{ width: `${finding.confidence * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
