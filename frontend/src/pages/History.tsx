import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSearch, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import AppShell from "@/components/layout/AppShell";
import ErrorBanner from "@/components/common/ErrorBanner";
import { ApiError, apiDelete, apiGet } from "@/lib/api";
import { apiErrorMessage, formatDate, scoreBand } from "@/lib/severity";
import type { HistorySummary } from "@/lib/types";

export default function History() {
  const queryClient = useQueryClient();
  const { data, isError, isLoading } = useQuery({
    queryKey: ["history"],
    queryFn: () => apiGet<HistorySummary[]>("/history"),
    retry: false,
  });

  const items = isError ? [] : (data ?? []);

  const removeOne = useMutation({
    mutationFn: (id: string) => apiDelete<{ ok: boolean }>(`/history/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["history"] });
      toast.success("Analysis deleted");
    },
    onError: (err) =>
      toast.error(
        err instanceof ApiError
          ? apiErrorMessage(err.status, err.body)
          : "Could not delete that analysis.",
      ),
  });

  const clearAll = useMutation({
    mutationFn: () => apiDelete<{ deleted: number }>("/history"),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["history"] });
      toast.success(`Cleared ${result.deleted} ${result.deleted === 1 ? "analysis" : "analyses"}`);
    },
    onError: () => toast.error("Could not clear the history."),
  });

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">History</h1>
          <p className="mt-1.5 text-sm text-slate-400">
            Analyses you chose to save. SENTINEL stores the report only — never your source code.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/analyzer"
            className={buttonVariants({ variant: "outline", size: "sm" })}
            data-testid="history-analyze-link"
          >
            <FileSearch className="mr-2 size-4" />
            New analysis
          </Link>
          <Button
            variant="destructive"
            size="sm"
            disabled={items.length === 0 || clearAll.isPending}
            onClick={() => clearAll.mutate()}
            data-testid="clear-history-btn"
          >
            <Trash2 className="mr-2 size-4" />
            Clear all
          </Button>
        </div>
      </div>

      {isError ? (
        <ErrorBanner
          message="Your saved history is unavailable right now."
          testId="history-error"
          className="mb-4"
        />
      ) : null}

      <Card className="border-slate-800 bg-slate-900/50">
        <CardHeader>
          <CardTitle className="text-base">
            Saved analyses
            <span className="ml-2 font-mono text-xs font-normal text-slate-500">
              {items.length}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div
              className="flex flex-col items-center gap-3 py-14 text-center"
              data-testid="history-empty-state"
            >
              <FileSearch className="size-6 text-slate-600" />
              <p className="text-sm text-slate-300">
                {isLoading ? "Loading your history…" : "No saved analyses yet."}
              </p>
              <p className="max-w-sm text-xs text-slate-500">
                Save a scan from the Analyzer to track how a file&apos;s score changes over time.
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-slate-800">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Date</TableHead>
                    <TableHead>File</TableHead>
                    <TableHead>Overall</TableHead>
                    <TableHead>Security</TableHead>
                    <TableHead>Issues</TableHead>
                    <TableHead className="hidden sm:table-cell">Critical / High</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => {
                    const band = item.overall_score === null ? null : scoreBand(item.overall_score);
                    return (
                      <TableRow key={item.id} data-testid={`history-row-${item.id}`}>
                        <TableCell className="whitespace-nowrap text-xs text-slate-400">
                          {formatDate(item.created_at)}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-slate-200">
                          {item.file_name}
                        </TableCell>
                        <TableCell>
                          <span
                            className="font-mono text-sm font-semibold tabular-nums"
                            style={{ color: band?.hex ?? "#94A3B8" }}
                          >
                            {item.overall_score ?? "—"}
                          </span>
                        </TableCell>
                        <TableCell className="font-mono text-sm tabular-nums text-slate-300">
                          {item.security_score ?? "—"}
                        </TableCell>
                        <TableCell className="font-mono text-sm tabular-nums text-slate-300">
                          {item.total_issues}
                        </TableCell>
                        <TableCell className="hidden font-mono text-sm tabular-nums text-slate-400 sm:table-cell">
                          {item.critical_issues} / {item.high_issues}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Delete analysis of ${item.file_name}`}
                            onClick={() => removeOne.mutate(item.id)}
                            disabled={removeOne.isPending}
                            data-testid={`delete-history-${item.id}`}
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
