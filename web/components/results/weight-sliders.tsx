"use client";

import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DEFAULT_WEIGHTS, DIMENSIONS, type Weights } from "@/lib/ranking";

export function WeightSliders({
  weights,
  onChange,
  formula,
}: {
  weights: Weights;
  onChange: (weights: Weights) => void;
  formula?: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-4 shadow-soft">
      <div className="flex items-center justify-between">
        <h2 className="font-sans text-sm font-medium tracking-normal">Ranking weights</h2>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Reset weights"
          onClick={() => onChange({ ...DEFAULT_WEIGHTS })}
        >
          <RotateCcw className="h-3.5 w-3.5" /> Reset
        </Button>
      </div>
      <div className="mt-2 space-y-3">
        {DIMENSIONS.map(({ key, label }) => (
          <label key={key} className="block text-xs text-muted-foreground">
            <span className="flex justify-between">
              {label}
              <span className="tabular-nums">{Math.round(weights[key] * 100)}%</span>
            </span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={weights[key]}
              onChange={(e) => onChange({ ...weights, [key]: Number(e.target.value) })}
              className="mt-1 w-full accent-[hsl(var(--primary))]"
              aria-label={`${label} weight`}
            />
          </label>
        ))}
      </div>
      {formula && (
        <p className="mt-3 border-t pt-2 text-[11px] leading-snug text-muted-foreground" title={formula}>
          <span className="font-medium">How scores combine:</span> {formula}
        </p>
      )}
    </div>
  );
}
