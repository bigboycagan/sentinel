import { useRef, useState } from "react";
import { FileCode2, Upload, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatBytes } from "@/lib/severity";

export interface LoadedFile {
  name: string;
  size: number;
  language: string;
}

export default function FileUpload({
  file,
  status,
  onLoad,
  onReject,
  onClear,
  maxBytes,
  extensions,
  hintExtensions,
}: {
  file: LoadedFile | null;
  status: string;
  onLoad: (name: string, size: number, code: string) => void;
  onReject: (message: string) => void;
  onClear: () => void;
  maxBytes: number;
  /** Every extension the engine accepts — the file's own extension picks the analyzer. */
  extensions: string[];
  /** Extensions of the currently selected language, shown in the hint copy. */
  hintExtensions?: string[];
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const accept = extensions.join(",");
  const hint = (hintExtensions?.length ? hintExtensions : extensions).slice(0, 3);

  // Files are read in the browser as TEXT and posted as a string — never executed.
  const handleFile = (picked: File) => {
    const name = picked.name.toLowerCase();
    if (!extensions.some((extension) => name.endsWith(extension))) {
      onReject(
        `Unsupported file type. SENTINEL currently supports: ${extensions.join(", ")}.`,
      );
      return;
    }
    if (picked.size > maxBytes) {
      onReject(
        `That file is ${formatBytes(picked.size)}, over the ${formatBytes(maxBytes)} limit. Raise it in Settings.`,
      );
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => onReject("The file could not be read. Try again.");
    reader.onload = () => onLoad(picked.name, picked.size, String(reader.result ?? ""));
    reader.readAsText(picked);
  };

  return (
    <div
      data-testid="file-upload-dropzone"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const dropped = e.dataTransfer.files?.[0];
        if (dropped) handleFile(dropped);
      }}
      className={`rounded-lg border border-dashed px-4 py-4 transition-colors duration-200 ${
        dragging ? "border-emerald-500/70 bg-emerald-500/5" : "border-slate-800 bg-slate-900/40"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        data-testid="file-input"
        onChange={(e) => {
          const picked = e.target.files?.[0];
          if (picked) handleFile(picked);
          e.target.value = "";
        }}
      />

      {file ? (
        <div className="flex flex-wrap items-center gap-3" data-testid="uploaded-file-card">
          <FileCode2 className="size-5 shrink-0 text-emerald-400" />
          <div className="min-w-0 flex-1">
            <p
              className="truncate font-mono text-sm text-slate-200"
              data-testid="uploaded-file-name"
            >
              {file.name}
            </p>
            <p className="mt-0.5 text-xs text-slate-500" data-testid="uploaded-file-meta">
              {formatBytes(file.size)} · {file.language}
            </p>
          </div>
          <Badge variant="outline" className="shrink-0" data-testid="uploaded-file-status">
            {status}
          </Badge>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClear}
            aria-label="Clear file"
            data-testid="clear-file-btn"
          >
            <X className="size-4" />
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Upload className="size-5 shrink-0 text-slate-500" />
            <div>
              <p className="text-sm text-slate-300">
                Drop a {hint.join(" / ")} file here
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                Up to {formatBytes(maxBytes)} · never executed, parsed as text only
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => inputRef.current?.click()}
            data-testid="browse-file-btn"
          >
            Browse file
          </Button>
        </div>
      )}
    </div>
  );
}
