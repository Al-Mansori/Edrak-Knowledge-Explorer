import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { getPdfObjectUrl } from "../../api"; // adjust path if needed
import { useStore } from "../../store";

/**
 * PDF tab: fetch & display selected document's PDF
 * - fills available height, iframe stretches fully
 */
export function PDFTab() {
  const { selectedDoc } = useStore();
  const [pdfSrc, setPdfSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let revokeUrl: string | null = null;
    setPdfSrc(null);
    setErr(null);

    if (!selectedDoc?.pdf_filename) return;

    setLoading(true);
    getPdfObjectUrl(selectedDoc.pdf_filename)
      .then((url) => {
        revokeUrl = url;
        setPdfSrc(url);
      })
      .catch((e: any) => setErr(String(e?.message || e)))
      .finally(() => setLoading(false));

  return () => {
      if (revokeUrl) URL.revokeObjectURL(revokeUrl);
    };
  }, [selectedDoc?.pdf_filename]);

  return (
    // Make this view fill the screen and allow children to grow
    <div className="h-screen max-h-screen p-4 mx-auto flex flex-col">
      <Card className="flex-1 flex flex-col min-h-0">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            PDFs
          </CardTitle>
        </CardHeader>

        {/* flex-1 + min-h-0 lets the viewer grow to full height */}
        <CardContent className="flex-1 min-h-0 flex flex-col gap-3 pb-0">
          <div className="text-sm text-muted-foreground">
            {selectedDoc
              ? `Selected: ${selectedDoc.title || selectedDoc.id}`
              : "Select a document from the sidebar to view its PDF."}
          </div>

          {/* The viewer takes all remaining height */}
          <div className="flex-1 min-h-0 rounded-md border overflow-hidden">
            {!selectedDoc ? (
              <div className="p-4 text-sm opacity-70">No document selected.</div>
            ) : err ? (
              <div className="p-4 text-sm text-red-600">{err}</div>
            ) : loading ? (
              <div className="p-4 text-sm opacity-70">Loading PDF…</div>
            ) : pdfSrc ? (
              <iframe
                title={selectedDoc.title || selectedDoc.id}
                src={pdfSrc}
                className="w-full h-full border-0"
              />
            ) : (
              <div className="p-4 text-sm opacity-70">No PDF available.</div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
