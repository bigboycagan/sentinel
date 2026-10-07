import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

/** Polished, non-technical error banner. Never renders a stack trace. */
export default function ErrorBanner({
  message,
  testId = "error-banner",
  className,
}: {
  message: string;
  testId?: string;
  className?: string;
}) {
  return (
    <div
      role="alert"
      data-testid={testId}
      className={cn(
        "flex items-start gap-3 rounded-lg border border-red-900/70 bg-red-950/35 px-4 py-3 animate-rise",
        className,
      )}
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-red-400" />
      <p className="text-sm leading-relaxed text-red-100/90">{message}</p>
    </div>
  );
}
