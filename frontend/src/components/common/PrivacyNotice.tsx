import { Lock } from "lucide-react";
import { cn } from "@/lib/utils";

/** The product's privacy promise. Shown wherever code is submitted. */
export default function PrivacyNotice({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border border-emerald-900/60 bg-emerald-950/30 px-4 py-3",
        className,
      )}
      data-testid="privacy-notice"
    >
      <Lock className="mt-0.5 size-4 shrink-0 text-emerald-400" />
      <p className="text-sm leading-relaxed text-emerald-100/85">
        Your source code is analyzed by SENTINEL without sending it to an external AI service.
      </p>
    </div>
  );
}
