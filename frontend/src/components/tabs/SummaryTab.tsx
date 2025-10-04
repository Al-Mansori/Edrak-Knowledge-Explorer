// src/components/tabs/SummaryTab.tsx
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks"; // 👈 add this
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { ScrollArea } from "../ui/scroll-area";
import { FileText } from "lucide-react";

import { useStore } from "../../store";
import { getSummary } from "../../api";

// Small helper: if text looks double-escaped, unescape common sequences.
function normalizeMarkdown(s: string): string {
  // If it already contains real newlines, leave it.
  if (s.includes("\n")) return s;

  // If it has escaped sequences, unescape them.
  if (s.includes("\\n") || s.includes("\\t") || s.includes("\\r")) {
    return s
      .replace(/\\r\\n/g, "\n")
      .replace(/\\n/g, "\n")
      .replace(/\\t/g, "\t")
      .replace(/\r/g, "\n"); // fallback
  }
  return s;
}

export function SummaryTab() {
  const { selectedDoc } = useStore();
  const [md, setMd] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setMd(null);
    setErr(null);

    if (!selectedDoc?.summary_filename) return;

    setLoading(true);
    getSummary<string>(selectedDoc.summary_filename)
      .then((res) => {
        if (cancelled) return;
        const raw =
          typeof res === "string"
            ? res
            : (res && typeof res === "object" && "content" in (res as any) && (res as any).content) || "";

        const normalized = normalizeMarkdown(String(raw ?? "").trim());
        setMd(normalized);
      })
      .catch((e: any) => !cancelled && setErr(String(e?.message || e)))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [selectedDoc?.summary_filename]);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {selectedDoc ? (selectedDoc.title || "Summary") : "Summary"}
          </CardTitle>
        </CardHeader>

        <CardContent>
          {!selectedDoc && <p className="text-sm text-muted-foreground">Select a document to view its summary.</p>}
          {selectedDoc && loading && <p className="text-sm text-muted-foreground">Loading summary…</p>}
          {selectedDoc && err && <p className="text-sm text-red-600">{err}</p>}

          {selectedDoc && !loading && !err && md && (
            <ScrollArea className="max-h-[70vh]">
              <div className="prose dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{md}</ReactMarkdown>
              </div>
            </ScrollArea>
          )}

          {selectedDoc && !loading && !err && !md && (
            <p className="text-sm text-muted-foreground">No summary content.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
