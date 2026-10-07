import { Link, useLocation } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";

const NAV = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Analyzer", to: "/analyzer" },
  { label: "History", to: "/history" },
  { label: "Rules", to: "/rules" },
  { label: "Settings", to: "/settings" },
];

export function BrandMark({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="group flex items-center gap-2.5" data-testid="brand-home-link">
      <span className="relative flex size-8 items-center justify-center rounded-md border border-emerald-500/30 bg-emerald-500/10">
        <ShieldCheck className="size-4 text-emerald-400" strokeWidth={2.2} />
      </span>
      <span className="font-mono text-sm font-bold tracking-[0.22em] text-slate-100 transition-colors duration-200 group-hover:text-emerald-300">
        SENTINEL
      </span>
    </Link>
  );
}

export function LocalEngineBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-emerald-300",
        className,
      )}
      data-testid="local-engine-badge"
    >
      <span className="size-1.5 animate-pulse-dot rounded-full bg-emerald-400" />
      Local engine only
    </span>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();

  return (
    <div className="min-h-svh bg-background">
      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-background/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 sm:px-6 lg:px-8">
          <BrandMark />
          <nav className="flex flex-1 items-center gap-1 overflow-x-auto" aria-label="Main">
            {NAV.map((item) => {
              const active = pathname === item.to || pathname.startsWith(`${item.to}/`);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  data-testid={`nav-${item.label.toLowerCase()}-link`}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "relative shrink-0 rounded-md px-3 py-2 text-sm transition-colors duration-200",
                    active
                      ? "text-emerald-300"
                      : "text-slate-400 hover:text-slate-100",
                  )}
                >
                  {item.label}
                  {active ? (
                    <span className="absolute inset-x-3 -bottom-[13px] h-0.5 rounded-full bg-emerald-400" />
                  ) : null}
                </Link>
              );
            })}
          </nav>
          <LocalEngineBadge className="hidden lg:inline-flex" />
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">{children}</main>
      <Toaster richColors />
    </div>
  );
}
