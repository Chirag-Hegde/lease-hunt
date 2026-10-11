"use client";

import { useMutation } from "@tanstack/react-query";
import {
  Check,
  ChevronDown,
  Copy,
  Mail,
  Minus,
  Plus,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { API_URL } from "@/lib/api-client";
import { cn } from "@/lib/utils";

type Tone = "friendly" | "firm" | "data-driven";
type Length = "short" | "standard" | "long";

type LeveragePoint = {
  id: string;
  text: string;
  evidence_ids: string[];
  kind: "price" | "reputation" | "lease" | "market" | "timing";
};

type Draft = {
  tone: Tone;
  subject: string;
  body: string;
  leverage_points: LeveragePoint[];
  asks: Array<{ kind: string; text: string }>;
};

type NegotiationResponse = {
  bundle: { listing_id: string; drafts: Draft[] };
  all_leverage_points: LeveragePoint[];
  evidence: Record<string, { excerpt: string | null; source_url: string | null; source_type: string }>;
};

const TONES: Tone[] = ["friendly", "firm", "data-driven"];
const KIND_LABEL: Record<LeveragePoint["kind"], string> = {
  price: "💰 price",
  reputation: "🏢 reputation",
  lease: "📄 lease",
  market: "📈 market",
  timing: "⏱ timing",
};
const LENGTHS: Length[] = ["short", "standard", "long"];

export default function NegotiationStudioPage() {
  const params = useParams<{ id: string }>();
  const listingId = params.id;
  const [tone, setTone] = useState<Tone>("friendly");
  const [length, setLength] = useState<Length>("standard");
  const [selected, setSelected] = useState<Set<string> | null>(null); // null = all
  const [bodies, setBodies] = useState<Record<Tone, string>>({} as Record<Tone, string>);
  const [subjects, setSubjects] = useState<Record<Tone, string>>({} as Record<Tone, string>);
  const [expandedPoint, setExpandedPoint] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const mutation = useMutation({
    mutationFn: async (vars: { selectedIds: string[] | null; length: Length }) => {
      const resp = await fetch(`${API_URL}/api/negotiations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          listing_id: listingId,
          selected_leverage_ids: vars.selectedIds,
          length: vars.length,
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      return (await resp.json()) as NegotiationResponse;
    },
    onSuccess: (data) => {
      const nextBodies = {} as Record<Tone, string>;
      const nextSubjects = {} as Record<Tone, string>;
      for (const draft of data.bundle.drafts) {
        nextBodies[draft.tone] = draft.body;
        nextSubjects[draft.tone] = draft.subject;
      }
      setBodies(nextBodies);
      setSubjects(nextSubjects);
    },
  });

  const regenerate = useCallback(
    (nextSelected: Set<string> | null, nextLength: Length) => {
      mutation.mutate({
        selectedIds: nextSelected ? Array.from(nextSelected) : null,
        length: nextLength,
      });
    },
    [mutation],
  );

  useEffect(() => {
    mutation.mutate({ selectedIds: null, length: "standard" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listingId]);

  const data = mutation.data;
  const allPoints = data?.all_leverage_points ?? [];
  const isSelected = (id: string) => selected == null || selected.has(id);

  const togglePoint = (id: string) => {
    const base = selected ?? new Set(allPoints.map((p) => p.id));
    const next = new Set(base);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
    regenerate(next, length);
  };

  const changeLength = (delta: number) => {
    const index = Math.min(Math.max(LENGTHS.indexOf(length) + delta, 0), LENGTHS.length - 1);
    const next = LENGTHS[index]!;
    if (next !== length) {
      setLength(next);
      regenerate(selected, next);
    }
  };

  const copyDraft = async () => {
    await navigator.clipboard.writeText(`Subject: ${subjects[tone] ?? ""}\n\n${bodies[tone] ?? ""}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const mailto = `mailto:?subject=${encodeURIComponent(subjects[tone] ?? "")}&body=${encodeURIComponent(bodies[tone] ?? "")}`;

  return (
    <div className="container max-w-6xl py-8">
      <div className="mb-6">
        <Link
          href={`/listings/${listingId}`}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          ← back to listing
        </Link>
        <h1 className="text-3xl">Negotiation Studio</h1>
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Every leverage point cites evidence. Nothing is ever sent automatically — you copy it.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        {/* Leverage sidebar */}
        <aside>
          <h2 className="mb-2 text-sm font-medium">Leverage points</h2>
          <p className="mb-3 text-xs text-muted-foreground">
            Toggle chips to include or drop them — the draft regenerates.
          </p>
          <div className="space-y-2">
            {allPoints.length === 0 && !mutation.isPending && (
              <p className="rounded-md border border-dashed p-4 text-xs text-muted-foreground">
                No leverage found yet. Run a search that analyzes this listing, or upload its
                lease, to give the Negotiator ammunition.
              </p>
            )}
            {allPoints.map((point) => (
              <div
                key={point.id}
                className={cn(
                  "rounded-lg border transition-colors",
                  isSelected(point.id) ? "border-primary/50 bg-primary/5" : "opacity-60",
                )}
              >
                <div className="flex items-start gap-2 p-2.5">
                  <input
                    type="checkbox"
                    checked={isSelected(point.id)}
                    onChange={() => togglePoint(point.id)}
                    aria-label={`Include leverage: ${point.text.slice(0, 60)}`}
                    className="mt-1 accent-[hsl(var(--primary))]"
                  />
                  <div className="min-w-0 flex-1">
                    <Badge variant="secondary" className="mb-1">
                      {KIND_LABEL[point.kind]}
                    </Badge>
                    <p className="text-xs leading-snug">{point.text}</p>
                  </div>
                  <button
                    type="button"
                    aria-label="Show evidence"
                    onClick={() => setExpandedPoint(expandedPoint === point.id ? null : point.id)}
                    className="shrink-0 p-1 text-muted-foreground hover:text-foreground"
                  >
                    <ChevronDown
                      className={cn(
                        "h-3.5 w-3.5 transition-transform",
                        expandedPoint === point.id && "rotate-180",
                      )}
                    />
                  </button>
                </div>
                {expandedPoint === point.id && (
                  <div className="space-y-1 border-t bg-muted/30 p-2.5">
                    {point.evidence_ids.map((eid) => {
                      const ev = data?.evidence[eid];
                      if (!ev) return null;
                      return (
                        <p key={eid} className="text-[11px] text-muted-foreground">
                          <Badge variant="outline" className="mr-1">
                            {ev.source_type}
                          </Badge>
                          “{ev.excerpt}”
                          {ev.source_url && (
                            <a
                              href={ev.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="ml-1 text-primary hover:underline"
                            >
                              source
                            </a>
                          )}
                        </p>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </aside>

        {/* Draft editor */}
        <section>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div role="tablist" aria-label="Tone" className="flex rounded-lg border p-1">
              {TONES.map((t) => (
                <button
                  key={t}
                  role="tab"
                  aria-selected={tone === t}
                  onClick={() => setTone(t)}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-sm capitalize transition-colors",
                    tone === t ? "bg-primary text-primary-foreground" : "text-muted-foreground",
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1.5">
              <Button variant="outline" size="sm" onClick={() => changeLength(-1)} disabled={length === "short"}>
                <Minus className="h-3.5 w-3.5" /> Shorter
              </Button>
              <Button variant="outline" size="sm" onClick={() => changeLength(1)} disabled={length === "long"}>
                <Plus className="h-3.5 w-3.5" /> Longer
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => regenerate(selected, length)}
                disabled={mutation.isPending}
              >
                <RefreshCw className={cn("h-3.5 w-3.5", mutation.isPending && "animate-spin")} />
                Regenerate
              </Button>
            </div>
          </div>

          <div className="rounded-lg border bg-card shadow-soft">
            <input
              value={subjects[tone] ?? ""}
              onChange={(e) => setSubjects({ ...subjects, [tone]: e.target.value })}
              aria-label="Email subject"
              className="w-full border-b bg-transparent p-3 font-medium focus:outline-none"
              placeholder={mutation.isPending ? "Drafting…" : "Subject"}
            />
            <textarea
              value={bodies[tone] ?? ""}
              onChange={(e) => setBodies({ ...bodies, [tone]: e.target.value })}
              aria-label="Email body"
              rows={18}
              className="w-full resize-y bg-transparent p-3 text-sm leading-relaxed focus:outline-none"
              placeholder={mutation.isPending ? "The Negotiator is writing…" : ""}
            />
          </div>

          <div className="mt-3 flex gap-2">
            <Button onClick={copyDraft}>
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? "Copied" : "Copy"}
            </Button>
            <a href={mailto} className="inline-flex">
              <Button variant="outline">
                <Mail className="h-4 w-4" /> Open in mail client
              </Button>
            </a>
          </div>
          {mutation.isError && (
            <p className="mt-2 text-sm text-severity-high">{String(mutation.error)}</p>
          )}
        </section>
      </div>
    </div>
  );
}
