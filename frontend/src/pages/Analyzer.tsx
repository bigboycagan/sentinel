import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Play, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import AppShell from "@/components/layout/AppShell";
import CodeEditor from "@/components/analyzer/CodeEditor";
import FileUpload, { type LoadedFile } from "@/components/analyzer/FileUpload";
import IssueExplorer from "@/components/analyzer/IssueExplorer";
import ResultsDashboard from "@/components/analyzer/ResultsDashboard";
import ErrorBanner from "@/components/common/ErrorBanner";
import PrivacyNotice from "@/components/common/PrivacyNotice";
import { ApiError, apiGet, apiPost } from "@/lib/api";
import { SAMPLES, samplesForLanguage } from "@/lib/samples";
import { apiErrorMessage } from "@/lib/severity";
import type {
  AnalysisReport,
  AppSettings,
  HistorySummary,
  LanguageOption,
} from "@/lib/types";

const DEFAULT_MAX_BYTES = 1_000_000;

// Used until /api/languages answers, so the page still renders with no backend.
const FALLBACK_LANGUAGES: LanguageOption[] = [
  { id: "python", label: "Python", extensions: [".py", ".pyi"] },
  { id: "javascript", label: "JavaScript", extensions: [".js", ".jsx", ".mjs", ".cjs"] },
  { id: "typescript", label: "TypeScript", extensions: [".ts", ".tsx", ".mts", ".cts"] },
];

export default function Analyzer() {
  const queryClient = useQueryClient();
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(SAMPLES[0].code);
  const [fileName, setFileName] = useState(SAMPLES[0].fileName);
  const [uploaded, setUploaded] = useState<LoadedFile | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Settings only shape the upload limit — the page must render without a backend.
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiGet<AppSettings>("/settings"),
    retry: false,
  });
  const maxBytes = settings?.max_file_size_bytes ?? DEFAULT_MAX_BYTES;

  const { data: languageData } = useQuery({
    queryKey: ["languages"],
    queryFn: () => apiGet<LanguageOption[]>("/languages"),
    retry: false,
  });
  const languages = languageData ?? FALLBACK_LANGUAGES;
  const activeLanguage = languages.find((item) => item.id === language) ?? languages[0];
  const languageLabels = Object.fromEntries(languages.map((item) => [item.id, item.label]));
  // Uploads accept any supported extension; the extension then selects the
  // language, so a .js file works even while Python is the active selection.
  const allExtensions = languages.flatMap((item) => item.extensions);
  const samples = samplesForLanguage(language);

  const analyze = useMutation({
    mutationFn: (payload: { code: string; file_name: string }) =>
      apiPost<AnalysisReport>("/analyze", { ...payload, language }),
    onSuccess: (result) => {
      setReport(result);
      setError(null);
      if (result.parse_error) {
        setError("Unable to parse this source file. Check the syntax and try again.");
      }
    },
    onError: (err) => {
      setReport(null);
      setError(
        err instanceof ApiError
          ? apiErrorMessage(err.status, err.body)
          : "Something went wrong while analyzing the code.",
      );
    },
  });

  const save = useMutation({
    mutationFn: () =>
      apiPost<HistorySummary>("/history", { code, file_name: fileName, language }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["history"] });
      toast.success("Analysis saved to history");
    },
    onError: (err) => {
      toast.error(
        err instanceof ApiError
          ? apiErrorMessage(err.status, err.body)
          : "Could not save this analysis.",
      );
    },
  });

  const status = analyze.isPending
    ? "Analyzing"
    : report
      ? report.parse_error
        ? "Parse error"
        : "Analyzed"
      : "Ready";

  const runAnalysis = () => {
    if (!code.trim()) {
      setReport(null);
      setError("Please provide source code to analyze.");
      return;
    }
    setError(null);
    analyze.mutate({ code, file_name: fileName || "untitled.py" });
  };

  const findings = useMemo(() => report?.findings ?? [], [report]);

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">Analyzer</h1>
        <p className="mt-1.5 text-sm text-slate-400">
          Paste or upload Python, JavaScript or TypeScript source. SENTINEL parses it locally —
          it is never executed.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left: input */}
        <div className="flex flex-col gap-4 lg:col-span-6">
          <PrivacyNotice />

          <Card className="border-slate-800 bg-slate-900/50">
            <CardContent className="space-y-4 pt-6">
              <div className="grid gap-2 sm:grid-cols-2">
                <div>
                  <label
                    className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500"
                    htmlFor="language-select"
                  >
                    Language
                  </label>
                  <Select
                    value={language}
                    onValueChange={(value: string) => {
                      if (value === language) return;
                      setLanguage(value);
                      const next = samplesForLanguage(value)[0];
                      if (next) {
                        setCode(next.code);
                        setFileName(next.fileName);
                      }
                      setUploaded(null);
                      setReport(null);
                      setError(null);
                    }}
                  >
                    <SelectTrigger
                      id="language-select"
                      className="mt-1.5"
                      data-testid="language-select"
                    >
                      <SelectValue>
                        {(value) => languageLabels[String(value)] ?? String(value)}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {languages.map((item) => (
                        <SelectItem
                          key={item.id}
                          value={item.id}
                          data-testid={`language-option-${item.id}`}
                        >
                          {item.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label
                    className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500"
                    htmlFor="sample-select"
                  >
                    Load a sample
                  </label>
                  <Select
                    value=""
                    onValueChange={(value: string) => {
                      const sample = SAMPLES.find((item) => item.id === value);
                      if (!sample) return;
                      setLanguage(sample.language);
                      setCode(sample.code);
                      setFileName(sample.fileName);
                      setUploaded(null);
                      setReport(null);
                      setError(null);
                    }}
                  >
                    <SelectTrigger
                      id="sample-select"
                      className="mt-1.5"
                      data-testid="sample-select"
                    >
                      <SelectValue>{() => "Choose a snippet…"}</SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {samples.map((sample) => (
                        <SelectItem
                          key={sample.id}
                          value={sample.id}
                          data-testid={`sample-option-${sample.id}`}
                        >
                          {sample.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <FileUpload
                file={uploaded}
                status={status}
                maxBytes={maxBytes}
                extensions={allExtensions}
                hintExtensions={activeLanguage?.extensions}
                onLoad={(name, size, text) => {
                  // The extension is authoritative: pick the matching language.
                  const matched = languages.find((item) =>
                    item.extensions.some((extension) => name.toLowerCase().endsWith(extension)),
                  );
                  const resolved = matched?.id ?? language;
                  setLanguage(resolved);
                  setUploaded({
                    name,
                    size,
                    language: matched?.label ?? languageLabels[resolved] ?? resolved,
                  });
                  setFileName(name);
                  setCode(text);
                  setReport(null);
                  setError(null);
                }}
                onReject={(message) => {
                  setUploaded(null);
                  setError(message);
                }}
                onClear={() => {
                  setUploaded(null);
                  setError(null);
                }}
              />

              <CodeEditor
                value={code}
                onChange={setCode}
                findings={findings}
                height="420px"
                language={language}
                fileName={fileName}
              />

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  onClick={runAnalysis}
                  disabled={analyze.isPending}
                  data-testid="analyze-code-btn"
                >
                  {analyze.isPending ? (
                    <Loader2 className="mr-2 size-4 animate-spin" />
                  ) : (
                    <Play className="mr-2 size-4" />
                  )}
                  {analyze.isPending ? "Analyzing…" : "Analyze"}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => save.mutate()}
                  disabled={!report || !!report.parse_error || save.isPending}
                  data-testid="save-analysis-btn"
                >
                  {save.isPending ? (
                    <Loader2 className="mr-2 size-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 size-4" />
                  )}
                  Save to history
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setCode("");
                    setReport(null);
                    setUploaded(null);
                    setError(null);
                  }}
                  data-testid="clear-code-btn"
                >
                  <Trash2 className="mr-2 size-4" />
                  Clear
                </Button>
                <span className="ml-auto font-mono text-xs text-slate-500">
                  {code.split("\n").length} lines
                </span>
              </div>

              {error ? <ErrorBanner message={error} testId="analysis-error" /> : null}
            </CardContent>
          </Card>
        </div>

        {/* Right: results */}
        <div className="flex flex-col gap-4 lg:col-span-6">
          {report && !report.parse_error ? (
            <>
              <ResultsDashboard report={report} />
              <IssueExplorer findings={findings} />
            </>
          ) : (
            <Card className="border-slate-800 bg-slate-900/50">
              <CardContent className="flex min-h-[320px] flex-col items-center justify-center gap-3 text-center">
                <div className="flex size-11 items-center justify-center rounded-lg border border-slate-800 bg-slate-950">
                  <Play className="size-4 text-slate-600" />
                </div>
                <p className="text-sm text-slate-300" data-testid="results-placeholder">
                  {report?.parse_error
                    ? "This file could not be parsed, so no scores were produced."
                    : "Run an analysis to see scores, charts and findings."}
                </p>
                <p className="max-w-sm text-xs text-slate-500">
                  {report?.parse_error
                    ? `Syntax error on line ${report.parse_error.line}: ${report.parse_error.message}`
                    : "SENTINEL reports a 0–100 score per category plus every rule it matched, with the exact line and a remediation note."}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  );
}
