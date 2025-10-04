// src/components/ChatArea.tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { MessageSquare, BarChart3, FileText, FileStack } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";

// Tabs
import { ChatTab } from "./tabs/ChatTab";
import { GraphTab } from "./tabs/GraphTab";
import { SummaryTab } from "./tabs/SummaryTab";
import { PDFTab } from "./tabs/PDFTab";

export function ChatArea() {
  return (
    <div className="flex-1 flex h-full min-h-0  flex-col h-full bg-background ">
      <div className="border-b border-border bg-card">
        <Tabs defaultValue="chat" className="w-full h-full flex flex-col">
          <TabsList className="w-full justify-start rounded-none h-12 bg-transparent p-0">
            <TabsTrigger
              value="chat"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent flex items-center gap-2"
            >
              <MessageSquare className="h-4 w-4" />
              Chat
            </TabsTrigger>

            <TabsTrigger
              value="graph"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent flex items-center gap-2"
            >
              <BarChart3 className="h-4 w-4" />
              Graph
            </TabsTrigger>

            <TabsTrigger
              value="summary"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent flex items-center gap-2"
            >
              <FileText className="h-4 w-4" />
              Summary
            </TabsTrigger>

            <TabsTrigger
              value="pdf"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent flex items-center gap-2"
            >
              <FileStack className="h-4 w-4" />
              PDF
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chat" className="flex-1 flex flex-col mt-0">
            <ChatTab />
          </TabsContent>

          <TabsContent value="graph" className="flex-1 mt-0 h-full  flex flex-col">
            <ScrollArea className="flex-1 min-h-0 h-full">
              <GraphTab />
            </ScrollArea>
          </TabsContent>

          <TabsContent value="summary" className="flex-1 mt-0 h-full  flex flex-col">
            <ScrollArea className="flex-1 min-h-0 h-full">
              <SummaryTab />
            </ScrollArea>
          </TabsContent>

          <TabsContent value="pdf" className="flex-1 mt-0 h-full  flex flex-col">
            <ScrollArea className="flex-1 min-h-0 h-full">
              <PDFTab />
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
