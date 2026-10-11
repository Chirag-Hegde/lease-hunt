export type Severity = "info" | "caution" | "high";

export type LeaseFinding = {
  id: string;
  clause_type: string;
  severity: Severity;
  explanation: string;
  why_it_matters: string;
  suggested_ask: string | null;
  citation: { page: number; bbox: [number, number, number, number]; quote: string };
  jurisdiction_note: {
    rule_id: string;
    text: string;
    source_url: string | null;
    verified: boolean;
  } | null;
  confidence: number;
};

export type LeaseAnalysis = {
  lease_id: string;
  risk_score: number;
  findings: LeaseFinding[];
  page_count: number;
  ocr_used: boolean;
  questions_for_landlord: string[];
  disclaimer: string;
};

export type LeaseResponse = {
  id: string;
  filename: string;
  listing_id: string | null;
  status: "pending" | "processing" | "finished" | "failed";
  page_count: number | null;
  ocr_used: boolean;
  risk_score: number | null;
  summary: {
    counts?: Record<Severity, number>;
    questions_for_landlord?: string[];
    rule_pack?: string;
  } | null;
  error: string | null;
  created_at: string;
  analysis: LeaseAnalysis | null;
};

export type SampleLease = { key: string; title: string; building_key: string };

export const SEVERITY_LABEL: Record<Severity, string> = {
  high: "High risk",
  caution: "Caution",
  info: "Info",
};

export const SEVERITY_HIGHLIGHT: Record<Severity, string> = {
  high: "rgba(225, 29, 72, 0.25)",
  caution: "rgba(217, 119, 6, 0.22)",
  info: "rgba(100, 116, 139, 0.18)",
};
