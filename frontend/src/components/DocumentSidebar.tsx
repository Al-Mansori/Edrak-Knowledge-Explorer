import { useEffect, useState } from "react";
import { Search, File } from "lucide-react";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import { listDocuments } from "../api";
import { useStore } from "../store";
import type { Document as AppDocument } from "../api";

export function DocumentSidebar() {
  const [query, setQuery] = useState("");
  const [documents, setDocuments] = useState<AppDocument[]>([]);
  const [loading, setLoading] = useState(false);

  const selectedDoc = useStore((s) => s.selectedDoc);
  const setSelectedDoc = useStore((s) => s.setSelectedDoc);

  useEffect(() => {
    let active = true;
    setLoading(true);
    listDocuments({ q: query })
      .then((docs) => active && setDocuments(docs))
      .catch((err) => {
        console.error("Failed to fetch documents:", err);
        setDocuments([]);
      })
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [query]);

  return (
    // Parent is h-screen; sidebar should be h-full here.
    <div className="w-80 bg-card border-r border-border flex h-full min-h-0 flex-col ">
      {/* Search Box */}
      <div className="p-4 border-b border-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-10 bg-red-900/20 border-red-500/30 focus:border-red-400 focus:ring-red-400/20"
          />
        </div>
      </div>

      {/* Scrollable list area */}
      <ScrollArea className="flex-1 min-h-0 h-full">
        <div className="p-2">
          {loading && <p className="p-4 text-sm text-muted-foreground">Loading…</p>}
          {!loading && documents.length === 0 && (
            <p className="p-4 text-sm text-muted-foreground">No documents found</p>
          )}

          {documents.map((doc) => {
            const isActive = selectedDoc?.id === doc.id;
            return (
              <div
                key={doc.id}
                onClick={() => setSelectedDoc(doc)}
                className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                  isActive ? "bg-accent text-accent-foreground" : "hover:bg-accent"
                } `}
              >
                <File className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="truncate">{doc.title}</p>
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
