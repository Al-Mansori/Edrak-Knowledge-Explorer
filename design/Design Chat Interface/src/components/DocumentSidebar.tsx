import { Search, File } from "lucide-react";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";

export function DocumentSidebar() {
  const documents = [
    { name: "Project Overview.pdf", size: "2.3 MB", date: "Oct 1" },
    { name: "Technical Requirements.docx", size: "1.8 MB", date: "Sep 30" },
    { name: "User Research Report.pdf", size: "4.1 MB", date: "Sep 28" },
    { name: "Design System Guide.pdf", size: "3.2 MB", date: "Sep 27" },
    { name: "API Documentation.md", size: "0.8 MB", date: "Sep 25" },
    { name: "Meeting Notes.docx", size: "0.5 MB", date: "Sep 24" },
    { name: "Wireframes.pdf", size: "5.2 MB", date: "Sep 22" },
    { name: "Brand Guidelines.pdf", size: "2.7 MB", date: "Sep 20" },
  ];

  return (
    <div className="w-80 bg-card border-r border-border flex flex-col h-full">
      {/* Search Box */}
      <div className="p-4 border-b border-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            className="pl-10 bg-red-900/20 border-red-500/30 focus:border-red-400 focus:ring-red-400/20"
          />
        </div>
      </div>

      {/* Documents List */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {documents.map((doc, index) => (
            <div
              key={index}
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors"
            >
              <File className="h-5 w-5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="truncate">{doc.name}</p>
                <p className="text-sm text-muted-foreground">
                  {doc.size} • {doc.date}
                </p>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}