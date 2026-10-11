import { API_URL, type RunDetail } from "@/lib/api-client";

import { ResultsExplorerClient } from "./results-client";

// Server component: fetch the finished run so the page (list, sliders,
// scores) renders complete on first paint — no skeleton swap, stable layout.
export default async function ResultsExplorerPage({ params }: { params: { id: string } }) {
  let initialRun: RunDetail | undefined;
  try {
    const resp = await fetch(`${API_URL}/api/runs/${params.id}`, { cache: "no-store" });
    if (resp.ok) initialRun = (await resp.json()) as RunDetail;
  } catch {
    // API unreachable during SSR — the client will fetch instead.
  }
  return <ResultsExplorerClient runId={params.id} initialRun={initialRun} />;
}
