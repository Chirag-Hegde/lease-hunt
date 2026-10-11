// Client-side mirror of the backend ranking formula so weight-slider
// re-ranking is instant. Formula: final = Σ(w_d · s_d) / Σ(w_d) over
// available dimensions.

export type Weights = {
  match: number;
  commute: number;
  value: number;
  reputation: number;
  lease_risk: number;
};

export type Scores = {
  match: number | null;
  commute: number | null;
  value: number | null;
  reputation: number | null;
  lease_risk: number | null;
};

export const DEFAULT_WEIGHTS: Weights = {
  match: 0.2,
  commute: 0.25,
  value: 0.2,
  reputation: 0.15,
  lease_risk: 0.2,
};

export const DIMENSIONS: Array<{ key: keyof Weights; label: string }> = [
  { key: "match", label: "Match" },
  { key: "commute", label: "Commute" },
  { key: "value", label: "Value" },
  { key: "reputation", label: "Reputation" },
  { key: "lease_risk", label: "Lease risk" },
];

export function finalScore(scores: Scores, weights: Weights): number {
  let weightedSum = 0;
  let weightTotal = 0;
  for (const { key } of DIMENSIONS) {
    const score = scores[key];
    const weight = weights[key];
    if (score != null && weight > 0) {
      weightedSum += score * weight;
      weightTotal += weight;
    }
  }
  return weightTotal > 0 ? Math.round((weightedSum / weightTotal) * 10) / 10 : 0;
}

export function scoreColor(score: number): string {
  if (score >= 75) return "hsl(var(--primary))";
  if (score >= 55) return "hsl(var(--accent))";
  return "hsl(var(--destructive))";
}
