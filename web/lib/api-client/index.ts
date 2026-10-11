import type { components } from "./schema";

export type SearchBriefInput = components["schemas"]["SearchBriefInput"];
export type Place = components["schemas"]["Place"];
export type BriefResponse = components["schemas"]["BriefResponse"];
export type RunSummary = components["schemas"]["RunSummary"];
export type RunDetail = components["schemas"]["RunDetail"];
export type ListingModel = components["schemas"]["ListingModel"];
export type ListingWithResults = components["schemas"]["ListingWithResults"];
export type ListingDetail = components["schemas"]["ListingDetail"];
export type Fee = components["schemas"]["Fee"];

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new ApiError(resp.status, body || resp.statusText);
  }
  return (await resp.json()) as T;
}

export const api = {
  createBrief: (body: { text?: string; brief?: SearchBriefInput }) =>
    request<BriefResponse>("/api/briefs", { method: "POST", body: JSON.stringify(body) }),
  createBriefPreview: (text: string) =>
    request<SearchBriefInput>("/api/briefs/parse", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  getBrief: (id: string) => request<BriefResponse>(`/api/briefs/${id}`),
  createRun: (briefId: string) =>
    request<{ run_id: string }>("/api/runs", {
      method: "POST",
      body: JSON.stringify({ brief_id: briefId }),
    }),
  getRun: (id: string) => request<RunDetail>(`/api/runs/${id}`),
  listRuns: () => request<RunSummary[]>("/api/runs"),
  resumeRun: (id: string, body: { approve: boolean; max_listings?: number | null }) =>
    request<RunSummary>(`/api/runs/${id}/resume`, { method: "POST", body: JSON.stringify(body) }),
  getListing: (id: string) => request<ListingDetail>(`/api/listings/${id}`),
  runEventsUrl: (id: string, after = 0) => `${API_URL}/api/runs/${id}/events?after=${after}`,
  uploadLease: async (file: File, listingId?: string | null) => {
    const form = new FormData();
    form.append("file", file);
    const query = listingId ? `?listing_id=${listingId}` : "";
    const resp = await fetch(`${API_URL}/api/leases${query}`, { method: "POST", body: form });
    if (!resp.ok) throw new ApiError(resp.status, await resp.text());
    return resp.json();
  },
  analyzeSampleLease: async (key: string, listingId?: string | null) => {
    const query = listingId ? `?listing_id=${listingId}` : "";
    const resp = await fetch(`${API_URL}/api/leases/samples/${key}${query}`, { method: "POST" });
    if (!resp.ok) throw new ApiError(resp.status, await resp.text());
    return resp.json();
  },
  listSampleLeases: () =>
    request<{ samples: Array<{ key: string; title: string; building_key: string }> }>(
      "/api/leases/samples",
    ),
  getLease: (id: string) => request<unknown>(`/api/leases/${id}`),
  leaseFileUrl: (id: string) => `${API_URL}/api/leases/${id}/file`,
};
