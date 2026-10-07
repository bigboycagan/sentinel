import { useMemo } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { createTheme } from "@uiw/codemirror-themes";
import { EditorView, Decoration, type DecorationSet } from "@codemirror/view";
import { StateField, type Extension } from "@codemirror/state";
import { tags as t } from "@lezer/highlight";
import type { Finding } from "@/lib/types";
import { SEVERITY_RANK, SEVERITY_STYLES } from "@/lib/severity";

const sentinelTheme = createTheme({
  theme: "dark",
  settings: {
    background: "#090D11",
    foreground: "#E2E8F0",
    caret: "#10B981",
    selection: "#1E3A4B",
    selectionMatch: "#1E3A4B",
    lineHighlight: "#131D24",
    gutterBackground: "#0B0F14",
    gutterForeground: "#475569",
    gutterBorder: "transparent",
    fontFamily: "'JetBrains Mono Variable', ui-monospace, monospace",
  },
  styles: [
    { tag: t.comment, color: "#546174", fontStyle: "italic" },
    { tag: [t.keyword, t.moduleKeyword], color: "#C084FC" },
    { tag: [t.string, t.special(t.string)], color: "#6EE7B7" },
    { tag: [t.number, t.bool, t.null], color: "#FBBF24" },
    { tag: [t.function(t.variableName), t.function(t.propertyName)], color: "#60A5FA" },
    { tag: [t.className, t.typeName], color: "#38BDF8" },
    { tag: t.definition(t.variableName), color: "#E2E8F0" },
    { tag: t.operator, color: "#94A3B8" },
    { tag: t.propertyName, color: "#CBD5E1" },
    { tag: t.variableName, color: "#E2E8F0" },
  ],
});

/** Per-line severity stripe + background tint for every finding on that line. */
function findingHighlighter(findings: Finding[]): Extension {
  const worstByLine = new Map<number, string>();
  for (const finding of findings) {
    const current = worstByLine.get(finding.line);
    if (!current || SEVERITY_RANK[finding.severity] < SEVERITY_RANK[current as never]) {
      worstByLine.set(finding.line, finding.severity);
    }
  }

  const field = StateField.define<DecorationSet>({
    create(state) {
      const marks = [];
      for (const [line, severity] of worstByLine) {
        if (line < 1 || line > state.doc.lines) continue;
        const hex = SEVERITY_STYLES[severity as keyof typeof SEVERITY_STYLES].hex;
        marks.push(
          Decoration.line({
            attributes: {
              style: `background: ${hex}1f; box-shadow: inset 2px 0 0 0 ${hex};`,
            },
          }).range(state.doc.line(line).from),
        );
      }
      return Decoration.set(marks, true);
    },
    update(value, tr) {
      return tr.docChanged ? value.map(tr.changes) : value;
    },
    provide: (f) => EditorView.decorations.from(f),
  });

  return [field];
}

export default function CodeEditor({
  value,
  onChange,
  findings = [],
  readOnly = false,
  height = "420px",
}: {
  value: string;
  onChange?: (next: string) => void;
  findings?: Finding[];
  readOnly?: boolean;
  height?: string;
}) {
  // Re-keyed by the findings signature so markers refresh after each analysis.
  const extensions = useMemo(
    () => [python(), findingHighlighter(findings)],
    [findings],
  );

  return (
    <div
      className="overflow-hidden rounded-lg border border-slate-800 bg-[#090D11]"
      data-testid="code-editor"
    >
      <CodeMirror
        value={value}
        height={height}
        theme={sentinelTheme}
        extensions={extensions}
        editable={!readOnly}
        onChange={onChange}
        basicSetup={{
          lineNumbers: true,
          foldGutter: false,
          highlightActiveLine: !readOnly,
          highlightActiveLineGutter: !readOnly,
          autocompletion: false,
          searchKeymap: false,
        }}
        placeholder="# Paste Python source here, or upload a .py file"
      />
    </div>
  );
}
