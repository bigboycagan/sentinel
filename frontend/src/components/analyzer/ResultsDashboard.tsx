import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "@/lib/recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ScoreGauge, { ScoreBar } from "@/components/analyzer/ScoreGauge";
import { SEVERITIES, SEVERITY_STYLES } from "@/lib/severity";
import type { AnalysisReport } from "@/lib/types";

function MetricCell({ label, value, testId }: { label: string; value: string; testId: string }) {
  return (
    <div className="rounded-md border border-slate-800/80 bg-slate-900/40 px-3 py-2.5" data-testid={testId}>
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-1 font-mono text-lg font-semibold tabular-nums text-slate-100">{value}</p>
    </div>
  );
}

export default function ResultsDashboard({ report }: { report: AnalysisReport }) {
  const { counts, metrics, scores, overall_score: overall } = report;

  const severityData = SEVERITIES.map((severity) => ({
    name: severity,
    count: counts[severity.toLowerCase() as keyof typeof counts] as number,
    fill: SEVERITY_STYLES[severity].hex,
  }));

  const radarData = scores
    ? [
        { axis: "Security", value: scores.security },
        { axis: "Quality", value: scores.quality },
        { axis: "Complexity", value: scores.complexity },
        { axis: "Maintainability", value: scores.maintainability },
      ]
    : [];

  return (
    <div className="space-y-4" data-testid="results-dashboard">
      <Card className="border-slate-800 bg-slate-900/50">
        <CardContent className="grid gap-6 pt-6 sm:grid-cols-[auto_1fr] sm:items-center">
          <ScoreGauge score={overall ?? 0} label="Overall score" />
          <div className="space-y-3.5">
            {scores ? (
              <>
                <ScoreBar label="Security" score={scores.security} testId="score-security" />
                <ScoreBar label="Code Quality" score={scores.quality} testId="score-quality" />
                <ScoreBar label="Complexity" score={scores.complexity} testId="score-complexity" />
                <ScoreBar
                  label="Maintainability"
                  score={scores.maintainability}
                  testId="score-maintainability"
                />
              </>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div
          className="rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-3"
          data-testid="count-total"
        >
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">Total</p>
          <p className="mt-1 font-mono text-2xl font-bold tabular-nums text-slate-50">
            {counts.total}
          </p>
        </div>
        {SEVERITIES.map((severity) => {
          const style = SEVERITY_STYLES[severity];
          const value = counts[severity.toLowerCase() as keyof typeof counts] as number;
          return (
            <div
              key={severity}
              className={`rounded-lg border px-3 py-3 ${style.badge}`}
              data-testid={`count-${severity.toLowerCase()}`}
            >
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] opacity-80">
                {severity}
              </p>
              <p className="mt-1 font-mono text-2xl font-bold tabular-nums">{value}</p>
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-slate-800 bg-slate-900/50">
          <CardHeader>
            <CardTitle className="text-base">Issues by severity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-56" data-testid="severity-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={severityData} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                  <CartesianGrid stroke="#1E293B" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "#94A3B8", fontSize: 11 }}
                    stroke="#334155"
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fill: "#94A3B8", fontSize: 11 }}
                    stroke="#334155"
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#111827",
                      border: "1px solid #1F2937",
                      borderRadius: 8,
                      color: "#F8FAFC",
                      fontSize: 12,
                    }}
                    formatter={(value: number) => [`${value}`, "Findings"]}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {severityData.map((entry) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/50">
          <CardHeader>
            <CardTitle className="text-base">Category scores</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-56" data-testid="category-radar-chart">
              {radarData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData} outerRadius="72%">
                    <PolarGrid stroke="#1E293B" />
                    <PolarAngleAxis
                      dataKey="axis"
                      tick={{ fill: "#94A3B8", fontSize: 11 }}
                    />
                    <Radar
                      dataKey="value"
                      stroke="#10B981"
                      fill="#10B981"
                      fillOpacity={0.28}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#111827",
                        border: "1px solid #1F2937",
                        borderRadius: 8,
                        color: "#F8FAFC",
                        fontSize: 12,
                      }}
                      formatter={(value: number) => [`${value}/100`, "Score"]}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <p className="pt-16 text-center text-sm text-slate-500">
                  Scores unavailable for an unparsable file.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-800 bg-slate-900/50">
        <CardHeader>
          <CardTitle className="text-base">Measured metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <MetricCell label="Lines" value={String(metrics.total_lines)} testId="metric-total-lines" />
            <MetricCell
              label="Source lines"
              value={String(metrics.source_lines)}
              testId="metric-source-lines"
            />
            <MetricCell label="Comments" value={String(metrics.comment_lines)} testId="metric-comments" />
            <MetricCell label="Blank" value={String(metrics.blank_lines)} testId="metric-blank" />
            <MetricCell
              label="Functions"
              value={String(metrics.function_count)}
              testId="metric-functions"
            />
            <MetricCell label="Classes" value={String(metrics.class_count)} testId="metric-classes" />
            <MetricCell
              label="Max complexity"
              value={metrics.max_complexity === null ? "—" : String(metrics.max_complexity)}
              testId="metric-max-complexity"
            />
            <MetricCell
              label="Avg complexity"
              value={metrics.avg_complexity === null ? "—" : String(metrics.avg_complexity)}
              testId="metric-avg-complexity"
            />
            <MetricCell
              label="Avg fn length"
              value={
                metrics.avg_function_length === null ? "—" : String(metrics.avg_function_length)
              }
              testId="metric-avg-fn-length"
            />
            <MetricCell
              label="Max nesting"
              value={metrics.max_nesting_depth === null ? "—" : String(metrics.max_nesting_depth)}
              testId="metric-max-nesting"
            />
            <MetricCell
              label="Maintainability"
              value={
                metrics.maintainability_index === null
                  ? "—"
                  : `${metrics.maintainability_index}/100`
              }
              testId="metric-maintainability-index"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
