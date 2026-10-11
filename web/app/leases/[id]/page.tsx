"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, ClipboardList, Copy, ShieldAlert } from "lucide-react";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { FindingCard } from "@/components/lease/finding-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { SEVERITY_LABEL, type LeaseResponse, type Severity } from "@/lib/lease-types";
import { scoreColor } from "@/lib/ranking";

const LeasePdfViewer = dynamic(
  () => import("@/components/lease/pdf-viewer").then((m) => m.LeasePdfViewer),
  { ssr: false, loading: () => <div className="skeleton h-[70vh]" /> },
);

function RiskDial({ score }: { score: number }) {
  const radius = 54;
  const circumference = Math.PI * radius; // half circle
  const filled = (score / 100) * circumference;
  return (
    <div className="relative h-20 w-32" role="img" aria-label={`Lease risk score ${score} of 100`}>
      <svg viewBox="0 0 128 72" className="h-full w-full">
        <path
          d="M 10 66 A 54 54 0 0 1 118 66"
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={10}
          strokeLinecap="round"
        />
        <path
          d="M 10 66 A 54 54 0 0 1 118 66"
          fill="none"
          stroke={scoreColor(100 - score)}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
        />
      </svg>
      <div className="absolute inset-x-0 bottom-0 text-center">
        <span className="font-serif text-3xl tabular-nums">{score}</span>
        <span className="text-xs text-muted-foreground">/100 risk</span>
      </div>
    </div>
  );
}

export default function LeaseAnalyzerPage() {
  const params = useParams<{ id: string }>();
  const leaseId = params.id;
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<Severity | null>(null);
  const [copiedQuestions, setCopiedQuestions] = useState(false);

  const { data } = useQuery({
    queryKey: ["lease", leaseId],
    queryFn: async () => (await api.getLease(leaseId)) as LeaseResponse,
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "processing"
        ? 1200
        : false,
  });

  const analysis = data?.analysis ?? null;
  const findings = useMemo(
    () =>
      (analysis?.findings ?? []).filter(
        (f) => severityFilter == null || f.severity === severityFilter,
      ),
    [analysis, severityFilter],
  );
  const counts = data?.summary?.counts;

  // Keep the findings panel in sync when a highlight is clicked in the PDF.
  useEffect(() => {
    if (!selectedId) return;
    document
      .getElementById(`finding-${selectedId}`)
      ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [selectedId]);

  const copyQuestions = async () => {
    const questions = analysis?.questions_for_landlord ?? [];
    await navigator.clipboard.writeText(questions.map((q) => `- ${q}`).join("\n"));
    setCopiedQuestions(true);
    setTimeout(() => setCopiedQuestions(false), 1500);
  };

  if (!data) {
    return (
      <div className="container space-y-4 py-8">
        <div className="skeleton h-12 w-80" />
        <div className="skeleton h-[70vh]" />
      </div>
    );
  }

  if (data.status === "pending" || data.status === "processing") {
    return (
      <div className="container flex min-h-[50vh] flex-col items-center justify-center gap-3 text-center">
        <div className="skeleton h-2 w-56" />
        <h1 className="text-2xl">Analyzing {data.filename}…</h1>
        <p className="text-sm text-muted-foreground">
          Extracting clauses, classifying against the taxonomy, checking the California rule pack.
        </p>
      </div>
    );
  }

  if (data.status === "failed") {
    return (
      <div className="container py-16 text-center">
        <h1 className="text-2xl">Analysis failed</h1>
        <p className="mt-2 text-sm text-muted-foreground">{data.error}</p>
      </div>
    );
  }

  return (
    <div className="container max-w-[1400px] py-6">
      {/* Disclaimer banner — always visible */}
      <p className="mb-4 flex items-center gap-2 rounded-lg border border-severity-caution/40 bg-severity-caution/10 px-3 py-2 text-xs">
        <ShieldAlert className="h-4 w-4 shrink-0 text-severity-caution" />
        Not legal advice. Verify with a local tenant rights organization or attorney.
      </p>

      {/* Summary header */}
      <div className="mb-6 flex flex-wrap items-center gap-6 rounded-lg border bg-card p-4 shadow-soft">
        <RiskDial score={data.risk_score ?? 0} />
        <div className="flex-1">
          <h1 className="text-2xl">{data.filename}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>{data.page_count} pages</span>
            {data.ocr_used && <Badge variant="caution">OCR used — verify accuracy</Badge>}
            {data.summary?.rule_pack && <span>rules: {data.summary.rule_pack}</span>}
          </div>
          <div className="mt-2 flex gap-2">
            {(["high", "caution", "info"] as const).map((severity) => (
              <button
                key={severity}
                type="button"
                aria-pressed={severityFilter === severity}
                onClick={() =>
                  setSeverityFilter(severityFilter === severity ? null : severity)
                }
              >
                <Badge
                  variant={severity}
                  className={severityFilter === severity ? "ring-2 ring-ring" : ""}
                >
                  {counts?.[severity] ?? 0} {SEVERITY_LABEL[severity].toLowerCase()}
                </Badge>
              </button>
            ))}
          </div>
        </div>
        {(analysis?.questions_for_landlord.length ?? 0) > 0 && (
          <div className="max-w-sm rounded-md border bg-muted/40 p-3">
            <div className="flex items-center justify-between gap-2">
              <h2 className="flex items-center gap-1.5 text-sm font-medium">
                <ClipboardList className="h-4 w-4" /> Questions for the landlord
              </h2>
              <Button variant="ghost" size="sm" onClick={copyQuestions}>
                {copiedQuestions ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                Copy all
              </Button>
            </div>
            <ul className="mt-1 max-h-28 list-disc overflow-y-auto pl-4 text-xs text-muted-foreground">
              {analysis?.questions_for_landlord.map((question, i) => (
                <li key={i}>{question}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Two-pane */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
        <LeasePdfViewer
          fileUrl={api.leaseFileUrl(leaseId)}
          findings={analysis?.findings ?? []}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        <div className="h-[calc(100vh-10rem)] space-y-3 overflow-y-auto pr-1">
          {findings.length === 0 ? (
            <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              {severityFilter
                ? `No ${severityFilter} findings.`
                : "No flagged clauses — this lease looks clean."}
            </p>
          ) : (
            findings.map((finding) => (
              <div key={finding.id} id={`finding-${finding.id}`}>
                <FindingCard
                  finding={finding}
                  selected={selectedId === finding.id}
                  onSelect={() => setSelectedId(finding.id)}
                />
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
