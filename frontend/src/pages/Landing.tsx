import { Link } from "react-router-dom";
import {
  Activity,
  FileSearch,
  GitBranch,
  Lock,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { BrandMark, LocalEngineBadge } from "@/components/layout/AppShell";
import CodeEditor from "@/components/analyzer/CodeEditor";
import type { Finding } from "@/lib/types";

const DEMO_CODE = `import random
import subprocess


def authenticate(user, password):
    api_key = "sk-live-8f2n9d0a7s6f5g4h3j2k"
    if password == "letmein2024":
        token = random.randint(0, 99999)
        return token
    return None


def ping(host):
    subprocess.run("ping -c 1 " + host, shell=True)
`;

// The exact findings SENTINEL's engine reports for DEMO_CODE — static preview only.
const DEMO_FINDINGS: Finding[] = [
  {
    rule_id: "SEC011",
    severity: "HIGH",
    category: "Security",
    title: "Hardcoded Secret / API Key",
    message: "A secret/API key appears to be directly embedded.",
    file: "demo.py",
    line: 6,
    column: 5,
    recommendation: "Move secrets to environment variables.",
    code_snippet: null,
  },
  {
    rule_id: "SEC001",
    severity: "HIGH",
    category: "Security",
    title: "Hardcoded Password",
    message: "A password is compared against a hardcoded literal.",
    file: "demo.py",
    line: 7,
    column: 5,
    recommendation: "Use a secret manager.",
    code_snippet: null,
  },
  {
    rule_id: "SEC009",
    severity: "MEDIUM",
    category: "Security",
    title: "Insecure Randomness",
    message: "A token is generated with the non-cryptographic random module.",
    file: "demo.py",
    line: 8,
    column: 9,
    recommendation: "Use the secrets module.",
    code_snippet: null,
  },
  {
    rule_id: "SEC006",
    severity: "HIGH",
    category: "Security",
    title: "Subprocess shell=True",
    message: "A subprocess is started with shell=True.",
    file: "demo.py",
    line: 15,
    column: 5,
    recommendation: "Pass an argument list with shell=False.",
    code_snippet: null,
  },
];

const PILLARS = [
  {
    icon: ShieldCheck,
    title: "Security analysis",
    body: "AST-level detection of hardcoded credentials, eval/exec, shell injection, unsafe deserialization, weak crypto, insecure randomness, SQL injection and path traversal.",
  },
  {
    icon: Wrench,
    title: "Code quality",
    body: "Unused variables and imports, unreachable code, excessive nesting, oversized functions and files, mutable default arguments, bare excepts and weak naming.",
  },
  {
    icon: Activity,
    title: "Complexity",
    body: "Cyclomatic complexity per function, average and maximum complexity, nesting depth, function and class counts, and line composition — all measured, never estimated.",
  },
  {
    icon: GitBranch,
    title: "Maintainability",
    body: "A radon-derived maintainability index built from Halstead volume, complexity and source lines, plus documentation coverage indicators.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-svh bg-background">
      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-background/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <BrandMark />
          <div className="flex items-center gap-3">
            <LocalEngineBadge className="hidden sm:inline-flex" />
            <Link
              to="/dashboard"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
              data-testid="landing-dashboard-link"
            >
              Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-7xl px-4 pb-16 pt-10 sm:px-6 lg:px-8 lg:pt-16">
          <div className="grid items-center gap-10 lg:grid-cols-12">
            <div className="lg:col-span-6">
              <Badge
                variant="outline"
                className="border-emerald-500/30 bg-emerald-500/10 font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-300"
              >
                Static analysis · no AI
              </Badge>
              <h1 className="mt-5 text-4xl font-bold tracking-tight text-slate-100 sm:text-5xl lg:text-6xl">
                SENTINEL
              </h1>
              <p className="mt-4 max-w-xl text-xl text-slate-300 sm:text-2xl">
                Know your code before it becomes a problem.
              </p>
              <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-400">
                Privacy-first static code analysis and security scanning for developers. SENTINEL
                parses your source with Python&apos;s own AST and a deterministic rule engine —
                every finding is reproducible, and nothing leaves this server.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  to="/analyzer"
                  className={buttonVariants({ size: "lg" })}
                  data-testid="hero-analyze-code-btn"
                >
                  <FileSearch className="mr-2 size-4" />
                  Analyze Code
                </Link>
                <Link
                  to="/rules"
                  className={buttonVariants({ variant: "outline", size: "lg" })}
                  data-testid="hero-explore-rules-btn"
                >
                  Explore Rules
                </Link>
              </div>
              <dl className="mt-10 grid max-w-md grid-cols-3 gap-4 border-t border-slate-800 pt-6">
                {[
                  ["32", "built-in rules"],
                  ["4", "score categories"],
                  ["0", "external calls"],
                ].map(([value, label]) => (
                  <div key={label}>
                    <dt className="font-mono text-2xl font-bold text-emerald-400">{value}</dt>
                    <dd className="mt-1 text-xs text-slate-500">{label}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <div className="lg:col-span-6">
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 shadow-2xl">
                <div className="mb-3 flex items-center justify-between px-1">
                  <span className="font-mono text-xs text-slate-500">demo.py</span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-red-400">
                    4 findings
                  </span>
                </div>
                <CodeEditor value={DEMO_CODE} findings={DEMO_FINDINGS} readOnly height="330px" />
                <p className="mt-3 px-1 text-xs text-slate-500">
                  Severity stripes mark the exact lines SENTINEL flags.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Pillars */}
        <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-100 sm:text-3xl">
            Four measured dimensions
          </h2>
          <p className="mt-3 max-w-2xl text-slate-400">
            Every analysis produces a 0&ndash;100 score per category plus a weighted overall score.
            The algorithm is deterministic and documented in the source — the same file always
            scores the same.
          </p>
          <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {PILLARS.map((pillar) => (
              <Card
                key={pillar.title}
                className="border-slate-800 bg-slate-900/50 transition duration-200 hover:-translate-y-0.5 hover:border-slate-700"
              >
                <CardContent className="pt-6">
                  <pillar.icon className="size-5 text-emerald-400" />
                  <h3 className="mt-4 text-lg font-medium tracking-tight text-slate-200">
                    {pillar.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{pillar.body}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Privacy */}
        <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="rounded-xl border border-emerald-950/80 bg-slate-900/70 p-8">
            <div className="flex items-start gap-4">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-emerald-500/25 bg-emerald-500/10">
                <Lock className="size-5 text-emerald-400" />
              </span>
              <div>
                <h2 className="text-2xl font-semibold tracking-tight text-slate-100">
                  Privacy-first architecture
                </h2>
                <p className="mt-3 max-w-3xl leading-relaxed text-slate-400">
                  Your source code is analyzed by SENTINEL without sending it to an external AI
                  service. There is no OpenAI, Gemini, Claude, Ollama or local LLM anywhere in the
                  pipeline, and no third-party code-analysis API.
                </p>
                <ul className="mt-6 grid gap-3 text-sm text-slate-300 sm:grid-cols-2">
                  {[
                    "Analysis runs entirely on this server — no outbound requests.",
                    "Source code is parsed as text and AST, never executed.",
                    "Nothing is stored unless you explicitly save an analysis.",
                    "Saved history keeps the report only — never your code.",
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-emerald-400" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        <footer className="border-t border-slate-800/80">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-8 sm:px-6 lg:px-8">
            <p className="text-sm text-slate-500">
              SENTINEL — privacy-first static code analysis. AI is intentionally not included in v1.
            </p>
            <Link
              to="/analyzer"
              className={buttonVariants({ variant: "outline", size: "sm" })}
              data-testid="footer-analyze-link"
            >
              Analyze Code
            </Link>
          </div>
        </footer>
      </main>
    </div>
  );
}
