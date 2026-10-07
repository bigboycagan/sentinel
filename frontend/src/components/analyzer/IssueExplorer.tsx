import { useMemo, useState } from "react";
import { ArrowUpDown, SearchX } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SEVERITIES, SEVERITY_RANK, SEVERITY_STYLES } from "@/lib/severity";
import type { Finding, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

type SortKey = "severity" | "line" | "rule_id" | "category";

const ALL = "__all__";

export function SeverityBadge({ severity }: { severity: Severity }) {
  const style = SEVERITY_STYLES[severity];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider",
        style.badge,
      )}
    >
      <span className={cn("size-1.5 rounded-full", style.dot)} />
      {severity}
    </span>
  );
}

export default function IssueExplorer({ findings }: { findings: Finding[] }) {
  const [severity, setSeverity] = useState<string>(ALL);
  const [category, setCategory] = useState<string>(ALL);
  const [ruleId, setRuleId] = useState<string>(ALL);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("severity");
  const [ascending, setAscending] = useState(true);
  const [selected, setSelected] = useState<Finding | null>(null);

  const categories = useMemo(
    () => Array.from(new Set(findings.map((f) => f.category))).sort(),
    [findings],
  );
  const ruleIds = useMemo(
    () => Array.from(new Set(findings.map((f) => f.rule_id))).sort(),
    [findings],
  );

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    const filtered = findings.filter((finding) => {
      if (severity !== ALL && finding.severity !== severity) return false;
      if (category !== ALL && finding.category !== category) return false;
      if (ruleId !== ALL && finding.rule_id !== ruleId) return false;
      if (
        term &&
        !`${finding.rule_id} ${finding.title} ${finding.message}`.toLowerCase().includes(term)
      ) {
        return false;
      }
      return true;
    });

    const direction = ascending ? 1 : -1;
    return [...filtered].sort((a, b) => {
      switch (sortKey) {
        case "line":
          return (a.line - b.line) * direction;
        case "rule_id":
          return a.rule_id.localeCompare(b.rule_id) * direction;
        case "category":
          return a.category.localeCompare(b.category) * direction;
        default:
          return (
            (SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || a.line - b.line) * direction
          );
      }
    });
  }, [findings, severity, category, ruleId, search, sortKey, ascending]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setAscending((prev) => !prev);
    } else {
      setSortKey(key);
      setAscending(true);
    }
  };

  const counts = useMemo(() => {
    const map = new Map<Severity, number>();
    for (const finding of findings) {
      map.set(finding.severity, (map.get(finding.severity) ?? 0) + 1);
    }
    return map;
  }, [findings]);

  return (
    <Card className="border-slate-800 bg-slate-900/50" data-testid="issue-explorer">
      <CardHeader>
        <CardTitle className="text-base">
          Issue explorer
          <span className="ml-2 font-mono text-xs font-normal text-slate-500">
            {visible.length} of {findings.length}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Button
            variant={severity === ALL ? "secondary" : "outline"}
            size="xs"
            onClick={() => setSeverity(ALL)}
            data-testid="severity-filter-all"
          >
            All ({findings.length})
          </Button>
          {SEVERITIES.map((level) => (
            <Button
              key={level}
              variant={severity === level ? "secondary" : "outline"}
              size="xs"
              onClick={() => setSeverity(severity === level ? ALL : level)}
              data-testid={`severity-filter-${level.toLowerCase()}`}
            >
              <span className={cn("mr-1.5 size-1.5 rounded-full", SEVERITY_STYLES[level].dot)} />
              {level} ({counts.get(level) ?? 0})
            </Button>
          ))}
        </div>

        <div className="grid gap-2 sm:grid-cols-3">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search rule or message…"
            data-testid="issue-search-input"
          />
          <Select value={category} onValueChange={(value: string) => setCategory(value)}>
            <SelectTrigger data-testid="category-filter-select">
              <SelectValue>
                {(value) => (value === ALL ? "All categories" : String(value))}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All categories</SelectItem>
              {categories.map((name) => (
                <SelectItem key={name} value={name}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={ruleId} onValueChange={(value: string) => setRuleId(value)}>
            <SelectTrigger data-testid="rule-filter-select">
              <SelectValue>
                {(value) => (value === ALL ? "All rules" : String(value))}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All rules</SelectItem>
              {ruleIds.map((id) => (
                <SelectItem key={id} value={id}>
                  {id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {visible.length === 0 ? (
          <div
            className="flex flex-col items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/40 py-12"
            data-testid="issue-explorer-empty"
          >
            <SearchX className="size-6 text-slate-600" />
            <p className="text-sm text-slate-400">
              {findings.length === 0
                ? "No issues detected in this file."
                : "No issues match the current filters."}
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-slate-800">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  {(
                    [
                      ["severity", "Severity"],
                      ["rule_id", "Rule"],
                      ["category", "Category"],
                    ] as [SortKey, string][]
                  ).map(([key, label]) => (
                    <TableHead key={key}>
                      <button
                        type="button"
                        onClick={() => toggleSort(key)}
                        className="inline-flex items-center gap-1 transition-colors duration-150 hover:text-slate-100"
                        data-testid={`sort-by-${key.replace("_", "-")}`}
                      >
                        {label}
                        <ArrowUpDown className="size-3" />
                      </button>
                    </TableHead>
                  ))}
                  <TableHead>Title</TableHead>
                  <TableHead className="hidden md:table-cell">File</TableHead>
                  <TableHead>
                    <button
                      type="button"
                      onClick={() => toggleSort("line")}
                      className="inline-flex items-center gap-1 transition-colors duration-150 hover:text-slate-100"
                      data-testid="sort-by-line"
                    >
                      Line
                      <ArrowUpDown className="size-3" />
                    </button>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((finding, index) => (
                  <TableRow
                    key={`${finding.rule_id}-${finding.line}-${finding.column}-${index}`}
                    onClick={() => setSelected(finding)}
                    className="cursor-pointer transition-colors duration-150"
                    data-testid={`issue-row-${index}`}
                  >
                    <TableCell>
                      <SeverityBadge severity={finding.severity} />
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-300">
                      {finding.rule_id}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">{finding.category}</TableCell>
                    <TableCell className="text-sm text-slate-200">{finding.title}</TableCell>
                    <TableCell className="hidden font-mono text-xs text-slate-500 md:table-cell">
                      {finding.file}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums text-slate-300">
                      {finding.line}:{finding.column}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>

      <Sheet open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
          {selected ? (
            <div data-testid="issue-detail-panel">
              <SheetHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={selected.severity} />
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {selected.rule_id}
                  </Badge>
                  <Badge variant="secondary" className="text-[10px]">
                    {selected.category}
                  </Badge>
                </div>
                <SheetTitle className="mt-2" data-testid="issue-detail-title">
                  {selected.title}
                </SheetTitle>
                <SheetDescription className="font-mono text-xs">
                  {selected.file}:{selected.line}:{selected.column}
                </SheetDescription>
              </SheetHeader>

              <div className="space-y-5 px-4 pb-6">
                <section>
                  <h4 className="font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-400">
                    Explanation
                  </h4>
                  <p
                    className="mt-2 text-sm leading-relaxed text-slate-300"
                    data-testid="issue-detail-message"
                  >
                    {selected.message}
                  </p>
                </section>

                {selected.code_snippet ? (
                  <section>
                    <h4 className="font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-400">
                      Problematic code
                    </h4>
                    <pre
                      className="mt-2 overflow-x-auto rounded-md border border-slate-800 bg-[#090D11] px-3 py-2.5 font-mono text-xs leading-6 text-slate-200"
                      data-testid="issue-detail-snippet"
                    >
                      <span className="mr-3 select-none text-slate-600">{selected.line}</span>
                      {selected.code_snippet}
                    </pre>
                  </section>
                ) : null}

                <section>
                  <h4 className="font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-400">
                    Recommendation
                  </h4>
                  <p
                    className="mt-2 text-sm leading-relaxed text-slate-300"
                    data-testid="issue-detail-recommendation"
                  >
                    {selected.recommendation}
                  </p>
                </section>
              </div>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </Card>
  );
}
