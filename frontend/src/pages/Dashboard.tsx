import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, FileSearch, ListChecks, ShieldCheck, TrendingUp } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import AppShell from "@/components/layout/AppShell";
import PrivacyNotice from "@/components/common/PrivacyNotice";
import { SeverityBadge } from "@/components/analyzer/IssueExplorer";
import { apiGet } from "@/lib/api";
import { formatDate, scoreBand } from "@/lib/severity";
import type { HistorySummary, RuleMeta } from "@/lib/types";

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  testId,
}: {
  icon: typeof ShieldCheck;
  label: string;
  value: string;
  hint: string;
  testId: string;
}) {
  return (
    <Card className="border-slate-800 bg-slate-900/50" data-testid={testId}>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500">
            {label}
          </p>
          <Icon className="size-4 text-emerald-400" />
        </div>
        <p className="mt-3 font-mono text-3xl font-bold tabular-nums text-slate-50">{value}</p>
        <p className="mt-1.5 text-xs text-slate-500">{hint}</p>
      </CardContent>
    </Card>
  );
}

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
}

export default function Dashboard() {
  const history = useQuery({
    queryKey: ["history"],
    queryFn: () => apiGet<HistorySummary[]>("/history"),
    retry: false,
  });
  const rules = useQuery({
    queryKey: ["rules"],
    queryFn: () => apiGet<RuleMeta[]>("/rules"),
    retry: false,
  });

  const items = history.isError ? [] : (history.data ?? []);
  const avgOverall = average(
    items.map((item) => item.overall_score).filter((value): value is number => value !== null),
  );
  const avgSecurity = average(
    items.map((item) => item.security_score).filter((value): value is number => value !== null),
  );
  const totalIssues = items.reduce((sum, item) => sum + item.total_issues, 0);
  const criticalIssues = items.reduce(
    (sum, item) => sum + item.critical_issues + item.high_issues,
    0,
  );

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">Dashboard</h1>
          <p className="mt-1.5 text-sm text-slate-400">
            Aggregated from the analyses you have saved. Nothing is recorded until you save one.
          </p>
        </div>
        <Link
          to="/analyzer"
          className={buttonVariants({ size: "sm" })}
          data-testid="dashboard-analyze-btn"
        >
          <FileSearch className="mr-2 size-4" />
          Analyze Code
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={ListChecks}
          label="Saved analyses"
          value={String(items.length)}
          hint={`${rules.data?.length ?? 0} rules available`}
          testId="stat-saved-analyses"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg overall score"
          value={avgOverall === null ? "—" : `${avgOverall}`}
          hint={avgOverall === null ? "No saved analyses yet" : scoreBand(avgOverall).label}
          testId="stat-avg-overall"
        />
        <StatCard
          icon={ShieldCheck}
          label="Avg security score"
          value={avgSecurity === null ? "—" : `${avgSecurity}`}
          hint={avgSecurity === null ? "No saved analyses yet" : scoreBand(avgSecurity).label}
          testId="stat-avg-security"
        />
        <StatCard
          icon={AlertTriangle}
          label="Total issues"
          value={String(totalIssues)}
          hint={`${criticalIssues} critical or high`}
          testId="stat-total-issues"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="border-slate-800 bg-slate-900/50 lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Recent analyses</CardTitle>
          </CardHeader>
          <CardContent>
            {items.length === 0 ? (
              <div
                className="flex flex-col items-center gap-3 py-12 text-center"
                data-testid="dashboard-empty-state"
              >
                <FileSearch className="size-6 text-slate-600" />
                <p className="text-sm text-slate-300">No saved analyses yet.</p>
                <p className="max-w-sm text-xs text-slate-500">
                  Run a scan in the Analyzer and choose &ldquo;Save to history&rdquo; to build up a
                  record over time.
                </p>
                <Link
                  to="/analyzer"
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                  data-testid="dashboard-empty-analyze-btn"
                >
                  Open the Analyzer
                </Link>
              </div>
            ) : (
              <ul className="divide-y divide-slate-800">
                {items.slice(0, 6).map((item) => {
                  const band = item.overall_score === null ? null : scoreBand(item.overall_score);
                  return (
                    <li
                      key={item.id}
                      className="flex flex-wrap items-center gap-3 py-3 first:pt-0"
                      data-testid={`dashboard-recent-${item.id}`}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-mono text-sm text-slate-200">
                          {item.file_name}
                        </p>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {formatDate(item.created_at)} · {item.total_issues} issues
                        </p>
                      </div>
                      <span
                        className="font-mono text-lg font-semibold tabular-nums"
                        style={{ color: band?.hex ?? "#94A3B8" }}
                      >
                        {item.overall_score ?? "—"}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <PrivacyNotice />
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader>
              <CardTitle className="text-base">Severity spread</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {(
                [
                  ["CRITICAL", items.reduce((s, i) => s + i.critical_issues, 0)],
                  ["HIGH", items.reduce((s, i) => s + i.high_issues, 0)],
                  ["MEDIUM", items.reduce((s, i) => s + i.medium_issues, 0)],
                  ["LOW", items.reduce((s, i) => s + i.low_issues, 0)],
                  ["INFO", items.reduce((s, i) => s + i.info_issues, 0)],
                ] as const
              ).map(([severity, count]) => (
                <div
                  key={severity}
                  className="flex items-center justify-between"
                  data-testid={`dashboard-spread-${severity.toLowerCase()}`}
                >
                  <SeverityBadge severity={severity} />
                  <span className="font-mono text-sm tabular-nums text-slate-200">{count}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
