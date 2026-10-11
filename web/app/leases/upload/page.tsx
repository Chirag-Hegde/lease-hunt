"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, Loader2, UploadCloud } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useRef, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import type { LeaseResponse, SampleLease } from "@/lib/lease-types";
import { cn } from "@/lib/utils";

function UploadInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const listingId = searchParams.get("listing");
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: samples } = useQuery({
    queryKey: ["lease-samples"],
    queryFn: () => api.listSampleLeases(),
  });

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF file.");
      return;
    }
    setBusy("your lease");
    setError(null);
    try {
      const lease = (await api.uploadLease(file, listingId)) as LeaseResponse;
      router.push(`/leases/${lease.id}`);
    } catch (e) {
      setBusy(null);
      setError(e instanceof Error ? e.message : "upload failed");
    }
  };

  const handleSample = async (sample: SampleLease) => {
    setBusy(sample.title);
    setError(null);
    try {
      const lease = (await api.analyzeSampleLease(sample.key, listingId)) as LeaseResponse;
      router.push(`/leases/${lease.id}`);
    } catch (e) {
      setBusy(null);
      setError(e instanceof Error ? e.message : "could not load sample");
    }
  };

  return (
    <div className="container max-w-2xl py-12">
      <h1 className="text-3xl">Analyze a lease</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Upload the lease PDF for {listingId ? "this unit" : "any unit"} — the Lease agent flags
        risky, unusual, and possibly unenforceable clauses with exact citations. Files are
        encrypted at rest and auto-deleted after 30 days.
      </p>

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) void handleFile(file);
        }}
        className={cn(
          "mt-6 flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed p-12 text-center transition-colors",
          dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50",
        )}
      >
        {busy ? (
          <>
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm">Dispatching the Lease agent on {busy}…</p>
          </>
        ) : (
          <>
            <UploadCloud className="h-8 w-8 text-primary" aria-hidden />
            <p className="text-sm font-medium">Drop your lease PDF here, or click to browse</p>
            <p className="text-xs text-muted-foreground">PDF only · up to 20MB · 100 pages</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
          }}
        />
      </div>

      {error && <p className="mt-3 text-sm text-severity-high">{error}</p>}

      <div className="mt-10">
        <h2 className="text-lg">…or try a sample lease</h2>
        <p className="text-sm text-muted-foreground">
          Six generated demo leases, from squeaky-clean to kitchen-sink bad.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {(samples?.samples ?? []).map((sample) => (
            <Card
              key={sample.key}
              role="button"
              tabIndex={0}
              onClick={() => !busy && handleSample(sample)}
              onKeyDown={(e) => e.key === "Enter" && !busy && handleSample(sample)}
              className="cursor-pointer transition-shadow hover:shadow-lifted"
            >
              <CardHeader className="p-4">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4 shrink-0 text-primary" />
                  {sample.title.replace("Residential Lease — ", "")}
                </CardTitle>
                <CardDescription className="text-xs">{sample.key.replace(/_/g, " ")}</CardDescription>
              </CardHeader>
              <CardContent className="p-0" />
            </Card>
          ))}
          {samples && samples.samples.length === 0 && (
            <p className="col-span-2 text-sm text-muted-foreground">
              No samples found — run <code className="font-mono">make seed</code> first.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function LeaseUploadPage() {
  return (
    <Suspense>
      <UploadInner />
    </Suspense>
  );
}
