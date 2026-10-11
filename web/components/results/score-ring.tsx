import { scoreColor } from "@/lib/ranking";

export function ScoreRing({
  score,
  size = 52,
  label,
}: {
  score: number;
  size?: number;
  label?: string;
}) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.max(0, Math.min(score, 100)) / 100) * circumference;
  return (
    <div
      className="relative inline-flex items-center justify-center"
      role="img"
      aria-label={`${label ?? "Score"}: ${Math.round(score)} out of 100`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={5}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={scoreColor(score)}
          strokeWidth={5}
          strokeDasharray={`${filled} ${circumference - filled}`}
          strokeLinecap="round"
          className="transition-[stroke-dasharray] duration-500"
        />
      </svg>
      <span className="absolute font-serif text-sm tabular-nums">{Math.round(score)}</span>
    </div>
  );
}
