import { scoreBand } from "@/lib/severity";

/** Circular SVG score ring, 0-100. Deterministic colour band, animated stroke. */
export default function ScoreGauge({
  score,
  label = "Overall",
  size = 168,
  testId = "overall-score-gauge",
}: {
  score: number;
  label?: string;
  size?: number;
  testId?: string;
}) {
  const band = scoreBand(score);
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.max(0, Math.min(100, score)) / 100);

  return (
    <div className="flex flex-col items-center gap-2" data-testid={testId}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            className="text-slate-800"
            strokeWidth={stroke}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={band.hex}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1)" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-mono text-4xl font-bold tabular-nums text-slate-50"
            data-testid={`${testId}-value`}
          >
            {score}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
            / 100
          </span>
        </div>
      </div>
      <div className="text-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">{label}</p>
        <p className={`mt-0.5 text-sm font-medium ${band.text}`} data-testid={`${testId}-band`}>
          {band.label}
        </p>
      </div>
    </div>
  );
}

/** Horizontal score bar for the four category scores. */
export function ScoreBar({
  label,
  score,
  testId,
}: {
  label: string;
  score: number;
  testId: string;
}) {
  const band = scoreBand(score);
  return (
    <div data-testid={testId}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm text-slate-400">{label}</span>
        <span
          className="font-mono text-sm font-semibold tabular-nums text-slate-100"
          data-testid={`${testId}-value`}
        >
          {score}
          <span className="text-slate-600">/100</span>
        </span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full"
          style={{
            width: `${Math.max(0, Math.min(100, score))}%`,
            background: band.hex,
            transition: "width 0.8s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
        />
      </div>
    </div>
  );
}
