"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import { SEVERITY_HIGHLIGHT, type LeaseFinding } from "@/lib/lease-types";
import { cn } from "@/lib/utils";

// Served from public/ (copied by scripts/copy-pdf-worker.mjs on dev/build).
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

const RENDER_WIDTH = 680;

export function LeasePdfViewer({
  fileUrl,
  findings,
  selectedId,
  onSelect,
}: {
  fileUrl: string;
  findings: LeaseFinding[];
  selectedId: string | null;
  onSelect: (findingId: string) => void;
}) {
  const [numPages, setNumPages] = useState(0);
  const [pageDims, setPageDims] = useState<Record<number, { width: number; height: number }>>({});
  const pageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const containerRef = useRef<HTMLDivElement>(null);

  const byPage = new Map<number, LeaseFinding[]>();
  for (const finding of findings) {
    const page = finding.citation.page;
    byPage.set(page, [...(byPage.get(page) ?? []), finding]);
  }

  // Scroll the PDF to the selected finding's highlight.
  useEffect(() => {
    if (!selectedId) return;
    const finding = findings.find((f) => f.id === selectedId);
    if (!finding) return;
    const pageEl = pageRefs.current[finding.citation.page];
    const container = containerRef.current;
    const dims = pageDims[finding.citation.page];
    if (!pageEl || !container) return;
    const scale = dims ? RENDER_WIDTH / dims.width : 1;
    const top = pageEl.offsetTop + finding.citation.bbox[1] * scale - 90;
    container.scrollTo({ top, behavior: "smooth" });
  }, [selectedId, findings, pageDims]);

  const onPageLoad = useCallback(
    (page: { pageNumber: number; width: number; height: number }) => {
      setPageDims((prev) => ({
        ...prev,
        [page.pageNumber]: { width: page.width, height: page.height },
      }));
    },
    [],
  );

  return (
    <div
      ref={containerRef}
      className="h-[calc(100vh-10rem)] overflow-y-auto rounded-lg border bg-muted/40 p-4"
    >
      <Document
        file={fileUrl}
        onLoadSuccess={({ numPages: n }) => setNumPages(n)}
        loading={<div className="skeleton h-[800px] w-[680px]" />}
        error={
          <p className="p-8 text-sm text-muted-foreground">
            Could not load the PDF. It may have been purged (leases auto-delete after 30 days).
          </p>
        }
      >
        {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNumber) => {
          const dims = pageDims[pageNumber];
          const scale = dims ? RENDER_WIDTH / dims.width : 1;
          return (
            <div
              key={pageNumber}
              ref={(el) => {
                pageRefs.current[pageNumber] = el;
              }}
              className="relative mx-auto mb-4 w-fit shadow-soft"
            >
              <Page
                pageNumber={pageNumber}
                width={RENDER_WIDTH}
                renderAnnotationLayer={false}
                renderTextLayer={false}
                onLoadSuccess={(page) =>
                  onPageLoad({
                    pageNumber,
                    width: page.getViewport({ scale: 1 }).width,
                    height: page.getViewport({ scale: 1 }).height,
                  })
                }
              />
              {(byPage.get(pageNumber) ?? []).map((finding) => {
                const [x0, y0, x1, y1] = finding.citation.bbox;
                return (
                  <button
                    key={finding.id}
                    type="button"
                    aria-label={`Flagged clause: ${finding.clause_type.replace(/_/g, " ")}`}
                    onClick={() => onSelect(finding.id)}
                    className={cn(
                      "absolute rounded-sm border transition-all",
                      selectedId === finding.id
                        ? "border-foreground/60 ring-2 ring-accent"
                        : "border-transparent hover:border-foreground/30",
                    )}
                    style={{
                      left: x0 * scale,
                      top: y0 * scale,
                      width: (x1 - x0) * scale,
                      height: (y1 - y0) * scale,
                      backgroundColor: SEVERITY_HIGHLIGHT[finding.severity],
                    }}
                  />
                );
              })}
            </div>
          );
        })}
      </Document>
    </div>
  );
}
