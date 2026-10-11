import { formatMinutes } from "@/lib/utils";

export type LegEstimate = {
  peak_minutes: number;
  offpeak_minutes: number;
  transfers: number | null;
  reliability_note: string | null;
};

export type CommuteData = {
  per_place: Array<{
    place_label: string;
    weight: number;
    by_mode: Record<string, LegEstimate>;
    best_mode: string;
    best_peak_minutes: number;
  }>;
  overall_score: number;
  formula: string;
};

const MODE_ICON: Record<string, string> = {
  drive: "🚗",
  transit: "🚆",
  bike: "🚲",
  walk: "🚶",
};

export function CommuteSection({ data }: { data: CommuteData }) {
  return (
    <div className="space-y-4">
      {data.per_place.map((place) => (
        <div key={place.place_label}>
          <h4 className="mb-1.5 text-sm font-medium">
            {place.place_label}
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              best: {MODE_ICON[place.best_mode]} {formatMinutes(place.best_peak_minutes)} at peak
            </span>
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="py-1.5 pr-4 font-normal">Mode</th>
                  <th className="py-1.5 pr-4 font-normal">Peak</th>
                  <th className="py-1.5 pr-4 font-normal">Off-peak</th>
                  <th className="py-1.5 font-normal">Notes</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(place.by_mode).map(([mode, leg]) => (
                  <tr key={mode} className="border-b border-border/50">
                    <td className="py-1.5 pr-4 capitalize">
                      {MODE_ICON[mode]} {mode}
                    </td>
                    <td className="py-1.5 pr-4 tabular-nums">
                      {formatMinutes(leg.peak_minutes)}
                    </td>
                    <td className="py-1.5 pr-4 tabular-nums text-muted-foreground">
                      {formatMinutes(leg.offpeak_minutes)}
                    </td>
                    <td className="py-1.5 text-xs text-muted-foreground">
                      {leg.transfers != null && leg.transfers > 0
                        ? `${leg.transfers} transfer${leg.transfers > 1 ? "s" : ""}. `
                        : ""}
                      {leg.reliability_note ?? ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
      <p className="text-xs text-muted-foreground" title={data.formula}>
        <span className="font-medium">How this is scored:</span> {data.formula}
      </p>
    </div>
  );
}
