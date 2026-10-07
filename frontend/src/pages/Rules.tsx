import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { SearchX } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import AppShell from "@/components/layout/AppShell";
import ErrorBanner from "@/components/common/ErrorBanner";
import { SeverityBadge } from "@/components/analyzer/IssueExplorer";
import { apiGet } from "@/lib/api";
import { CATEGORIES, SEVERITIES, SEVERITY_RANK } from "@/lib/severity";
import type { RuleMeta } from "@/lib/types";

const LANGUAGE_LABELS: Record<string, string> = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
};

export default function Rules() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["rules"],
    queryFn: () => apiGet<RuleMeta[]>("/rules"),
    retry: false,
  });

  const [severity, setSeverity] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [ruleLanguage, setRuleLanguage] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const rules = isError ? [] : (data ?? []);

  const languages = useMemo(
    () => Array.from(new Set(rules.map((rule) => rule.language))).sort(),
    [rules],
  );

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return rules
      .filter((rule) => {
        if (severity && rule.severity !== severity) return false;
        if (category && rule.category !== category) return false;
        if (ruleLanguage && rule.language !== ruleLanguage) return false;
        if (
          term &&
          !`${rule.rule_id} ${rule.title} ${rule.description}`.toLowerCase().includes(term)
        ) {
          return false;
        }
        return true;
      })
      .sort(
        (a, b) =>
          SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] ||
          a.rule_id.localeCompare(b.rule_id),
      );
  }, [rules, severity, category, ruleLanguage, search]);

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">Rules</h1>
        <p className="mt-1.5 text-sm text-slate-400">
          Every rule SENTINEL can match across Python, JavaScript and TypeScript, straight from
          the engine&apos;s registry. Each has a unique ID, a category, a severity and a
          remediation note.
        </p>
      </div>

      {isError ? (
        <ErrorBanner
          message="The rule catalog is unavailable right now."
          testId="rules-error"
          className="mb-4"
        />
      ) : null}

      <Card className="mb-6 border-slate-800 bg-slate-900/50">
        <CardContent className="space-y-3 pt-6">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by rule ID, name or description…"
            data-testid="rules-search-input"
          />
          <div className="flex flex-wrap gap-2">
            <Button
              variant={severity === null ? "secondary" : "outline"}
              size="xs"
              onClick={() => setSeverity(null)}
              data-testid="rules-severity-all"
            >
              All severities
            </Button>
            {SEVERITIES.map((level) => (
              <Button
                key={level}
                variant={severity === level ? "secondary" : "outline"}
                size="xs"
                onClick={() => setSeverity(severity === level ? null : level)}
                data-testid={`rules-severity-${level.toLowerCase()}`}
              >
                {level}
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={category === null ? "secondary" : "outline"}
              size="xs"
              onClick={() => setCategory(null)}
              data-testid="rules-category-all"
            >
              All categories
            </Button>
            {CATEGORIES.map((name) => (
              <Button
                key={name}
                variant={category === name ? "secondary" : "outline"}
                size="xs"
                onClick={() => setCategory(category === name ? null : name)}
                data-testid={`rules-category-${name.toLowerCase().replace(/\s+/g, "-")}`}
              >
                {name}
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={ruleLanguage === null ? "secondary" : "outline"}
              size="xs"
              onClick={() => setRuleLanguage(null)}
              data-testid="rules-language-all"
            >
              All languages
            </Button>
            {languages.map((name) => (
              <Button
                key={name}
                variant={ruleLanguage === name ? "secondary" : "outline"}
                size="xs"
                onClick={() => setRuleLanguage(ruleLanguage === name ? null : name)}
                data-testid={`rules-language-${name}`}
              >
                {LANGUAGE_LABELS[name] ?? name}
              </Button>
            ))}
          </div>
          <p className="font-mono text-xs text-slate-500" data-testid="rules-count">
            {visible.length} of {rules.length} rules
          </p>
        </CardContent>
      </Card>

      {visible.length === 0 ? (
        <div
          className="flex flex-col items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/40 py-16"
          data-testid="rules-empty-state"
        >
          <SearchX className="size-6 text-slate-600" />
          <p className="text-sm text-slate-400">
            {isLoading ? "Loading the rule catalog…" : "No rules match these filters."}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((rule) => (
            <Card
              key={rule.rule_id}
              className="border-slate-800 bg-slate-900/50 transition duration-200 hover:-translate-y-0.5 hover:border-slate-700"
              data-testid={`rule-card-${rule.rule_id}`}
            >
              <CardContent className="pt-6">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {rule.rule_id}
                  </Badge>
                  <SeverityBadge severity={rule.severity} />
                  <Badge variant="secondary" className="text-[10px]">
                    {LANGUAGE_LABELS[rule.language] ?? rule.language}
                  </Badge>
                </div>
                <h3 className="mt-3 text-base font-medium tracking-tight text-slate-100">
                  {rule.title}
                </h3>
                <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-emerald-400">
                  {rule.category}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-slate-400">{rule.description}</p>
                <p className="mt-3 border-t border-slate-800 pt-3 text-xs leading-relaxed text-slate-500">
                  <span className="font-semibold text-slate-400">Fix: </span>
                  {rule.recommendation}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  );
}
