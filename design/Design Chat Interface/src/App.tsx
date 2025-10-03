import { DocumentSidebar } from "./components/DocumentSidebar";
import { ChatArea } from "./components/ChatArea";

export default function App() {
  return (
    <div className="dark h-screen flex bg-background">
      <DocumentSidebar />
      <ChatArea />
    </div>
  );
}