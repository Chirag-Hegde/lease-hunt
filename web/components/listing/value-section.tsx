import { formatUSD } from "@/lib/utils";

export type PriceData = {
  comp_count: number;
  median_ppsf: number | null;
  listing_ppsf: number | null;
  percentile: number;
  fair_range_low: number;
  fair_range_high: number;
  total_monthly_cost: number;
  monthly_cost_breakdown: Record<string, number>;
  method: string;
};

const BAR_COLORS = [
  "hsl(var(--primary))",
  "hsl(var(--accent))",
  "hsl(var(--severity-info))",
  "hsl(175 40% 55%)",
  "hsl(29 60% 60%)",
];

export function ValueSection({ data, rent }: { data: PriceData; rent: number }) {
  const entries = Object.entries(data.monthly_cost_breakdown);
  const total = data.total_monthly_cost || 1;

  return (
    <div className="space-y-5">
      <div>
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-muted-foreground">Rent percentile vs. {data.comp_count} comps</span>
          <span className="font-serif text-lg tabular-nums">
            {Math.round(data.percentile)}
            <span className="text-xs text-muted-foreground">th</span>
          </span>
        </div>
        <div
          className="relative mt-2 h-3 rounded-full bg-gradient-to-r from-primary via-severity-caution to-severity-high"
          role="img"
          aria-label={`This listing rents above ${Math.round(data.percentile)}% of comparable units`}
        >
          <span
            className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-foreground shadow"
            style={{ left: `${Math.min(Math.max(data.percentile, 2), 98)}%` }}
          />
        </div>
        <p className="mt-2 text-sm">
          Fair range for similar units:{" "}
          <strong>
            {formatUSD(data.fair_range_low)}–{formatUSD(data.fair_range_high)}
          </strong>
          {rent > data.fair_range_high && (
            <span className="text-severity-high">
              {" "}
              — this unit is {formatUSD(rent - data.fair_range_high)} above it
            </span>
          )}
          {rent < data.fair_range_low && (
            <span className="text-primary"> — priced below the range</span>
          )}
        </p>
        {data.listing_ppsf != null && data.median_ppsf != null && (
          <p className="text-xs text-muted-foreground">
            ${data.listing_ppsf}/sqft vs. ${data.median_ppsf}/sqft comp median
          </p>
        )}
      </div>

      <div>
        <h4 className="text-sm font-medium">
          True monthly cost: {formatUSD(data.total_monthly_cost)}
        </h4>
        <div className="mt-2 flex h-5 overflow-hidden rounded-md" role="img" aria-label="Cost breakdown">
          {entries.map(([name, amount], i) => (
            <span
              key={name}
              title={`${name}: ${formatUSD(amount)}`}
              style={{
                width: `${(amount / total) * 100}%`,
                backgroundColor: BAR_COLORS[i % BAR_COLORS.length],
              }}
            />
          ))}
        </div>
        <ul className="mt-2 grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
          {entries.map(([name, amount], i) => (
            <li key={name} className="flex items-center gap-1.5">
              <span
                className="h-2 w-2 rounded-sm"
                style={{ backgroundColor: BAR_COLORS[i % BAR_COLORS.length] }}
              />
              {name}: {formatUSD(amount)}
            </li>
          ))}
        </ul>
      </div>

      <p className="text-xs text-muted-foreground">
        <span className="font-medium">Method:</span> {data.method}
      </p>
    </div>
  );
}
