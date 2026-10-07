import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import AppShell from "@/components/layout/AppShell";

export default function NotFound() {
  return (
    <AppShell>
      <div
        className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center"
        data-testid="not-found-page"
      >
        <Compass className="size-7 text-slate-600" />
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">Page not found</h1>
        <p className="max-w-sm text-sm text-slate-400">
          That route does not exist in SENTINEL. Head to the Analyzer to scan a file.
        </p>
        <Link
          to="/analyzer"
          className={buttonVariants({ size: "sm" })}
          data-testid="not-found-analyzer-link"
        >
          Open the Analyzer
        </Link>
      </div>
    </AppShell>
  );
}
