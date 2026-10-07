import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Moon, Save, Sun } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AppShell from "@/components/layout/AppShell";
import ErrorBanner from "@/components/common/ErrorBanner";
import { SeverityBadge } from "@/components/analyzer/IssueExplorer";
import { ApiError, apiGet, apiPut } from "@/lib/api";
import { apiErrorMessage, CATEGORIES, formatBytes } from "@/lib/severity";
import { applyTheme, getTheme, type ThemeMode } from "@/lib/theme";
import type { AppSettings, AppSettingsUpdate, RuleMeta } from "@/lib/types";

const MIN_KB = 10;
const MAX_KB = 10_000;

export default function Settings() {
  const queryClient = useQueryClient();
  const [theme, setTheme] = useState<ThemeMode>(getTheme());
  const [sizeKb, setSizeKb] = useState<string>("");
  const [disabled, setDisabled] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiGet<AppSettings>("/settings"),
    retry: false,
  });
  const rules = useQuery({
    queryKey: ["rules"],
    queryFn: () => apiGet<RuleMeta[]>("/rules"),
    retry: false,
  });

  // Seed the local form once the server state arrives.
  useEffect(() => {
    if (settings.data) {
      setSizeKb(String(Math.round(settings.data.max_file_size_bytes / 1024)));
      setDisabled(new Set(settings.data.disabled_rules));
    }
  }, [settings.data]);

  const grouped = useMemo(() => {
    const list = rules.data ?? [];
    return CATEGORIES.map((category) => ({
      category,
      rules: list.filter((rule) => rule.category === category),
    })).filter((group) => group.rules.length > 0);
  }, [rules.data]);

  const save = useMutation({
    mutationFn: (payload: AppSettingsUpdate) => apiPut<AppSettings>("/settings", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setError(null);
      toast.success("Settings saved");
    },
    onError: (err) =>
      setError(
        err instanceof ApiError
          ? apiErrorMessage(err.status, err.body)
          : "Could not save your settings.",
      ),
  });

  const handleSave = () => {
    const kb = Number(sizeKb);
    if (!Number.isFinite(kb) || kb < MIN_KB || kb > MAX_KB) {
      setError(`Maximum file size must be between ${MIN_KB} KB and ${MAX_KB} KB.`);
      return;
    }
    setError(null);
    save.mutate({
      max_file_size_bytes: Math.round(kb * 1024),
      disabled_rules: Array.from(disabled),
    });
  };

  const toggleRule = (ruleId: string, enabled: boolean) => {
    setDisabled((prev) => {
      const next = new Set(prev);
      if (enabled) next.delete(ruleId);
      else next.add(ruleId);
      return next;
    });
  };

  const enabledCount = (rules.data?.length ?? 0) - disabled.size;

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">Settings</h1>
        <p className="mt-1.5 text-sm text-slate-400">
          Analysis preferences apply to every scan. Rule toggles take effect on the next analysis.
        </p>
      </div>

      {error ? <ErrorBanner message={error} testId="settings-error" className="mb-4" /> : null}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-1">
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader>
              <CardTitle className="text-base">Appearance</CardTitle>
            </CardHeader>
            <CardContent>
              <Label className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500">
                Theme
              </Label>
              <div className="mt-2 flex gap-2">
                {(
                  [
                    ["dark", Moon, "Dark"],
                    ["light", Sun, "Light"],
                  ] as const
                ).map(([mode, Icon, label]) => (
                  <Button
                    key={mode}
                    variant={theme === mode ? "secondary" : "outline"}
                    size="sm"
                    onClick={() => {
                      setTheme(mode);
                      applyTheme(mode);
                    }}
                    data-testid={`theme-${mode}-btn`}
                  >
                    <Icon className="mr-2 size-4" />
                    {label}
                  </Button>
                ))}
              </div>
              <p className="mt-3 text-xs text-slate-500">
                SENTINEL is designed dark-first; the theme is remembered in this browser.
              </p>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader>
              <CardTitle className="text-base">Analysis preferences</CardTitle>
            </CardHeader>
            <CardContent>
              <Label
                htmlFor="max-file-size"
                className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500"
              >
                Maximum file size (KB)
              </Label>
              <Input
                id="max-file-size"
                type="number"
                min={MIN_KB}
                max={MAX_KB}
                value={sizeKb}
                onChange={(e) => setSizeKb(e.target.value)}
                className="mt-2"
                data-testid="max-file-size-input"
              />
              <p className="mt-2 text-xs text-slate-500" data-testid="max-file-size-hint">
                Currently enforced:{" "}
                {settings.data ? formatBytes(settings.data.max_file_size_bytes) : "—"}. Uploads and
                pasted source over this limit are rejected before parsing.
              </p>
              <Button
                className="mt-4 w-full"
                onClick={handleSave}
                disabled={save.isPending}
                data-testid="save-settings-btn"
              >
                {save.isPending ? (
                  <Loader2 className="mr-2 size-4 animate-spin" />
                ) : (
                  <Save className="mr-2 size-4" />
                )}
                Save settings
              </Button>
            </CardContent>
          </Card>
        </div>

        <Card className="border-slate-800 bg-slate-900/50 lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">
              Enabled rules
              <span className="ml-2 font-mono text-xs font-normal text-slate-500">
                {enabledCount} of {rules.data?.length ?? 0} active
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {grouped.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500" data-testid="settings-rules-empty">
                The rule catalog is unavailable right now.
              </p>
            ) : (
              grouped.map((group) => (
                <section key={group.category}>
                  <div className="flex items-center gap-2">
                    <h3 className="font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-400">
                      {group.category}
                    </h3>
                    <Badge variant="outline" className="text-[10px]">
                      {group.rules.length}
                    </Badge>
                  </div>
                  <ul className="mt-3 space-y-1.5">
                    {group.rules.map((rule) => {
                      const isEnabled = !disabled.has(rule.rule_id);
                      return (
                        <li
                          key={rule.rule_id}
                          className="flex items-center gap-3 rounded-md border border-slate-800/70 bg-slate-950/30 px-3 py-2"
                        >
                          <Checkbox
                            checked={isEnabled}
                            onCheckedChange={(checked) => toggleRule(rule.rule_id, checked === true)}
                            aria-label={`Toggle ${rule.rule_id}`}
                            data-testid={`rule-toggle-${rule.rule_id}`}
                          />
                          <span className="font-mono text-xs text-slate-400">{rule.rule_id}</span>
                          <span className="min-w-0 flex-1 truncate text-sm text-slate-200">
                            {rule.title}
                          </span>
                          <SeverityBadge severity={rule.severity} />
                        </li>
                      );
                    })}
                  </ul>
                </section>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
