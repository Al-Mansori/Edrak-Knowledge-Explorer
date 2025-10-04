// src/components/tabs/ChatTab.tsx
import { useState } from "react";
import { Send, Bot, User } from "lucide-react";
import { Textarea } from "../ui/textarea";
import { Button } from "../ui/button";
import { ScrollArea } from "../ui/scroll-area";
import { Avatar, AvatarFallback } from "../ui/avatar";
import { useStore } from "../../store";

export function ChatTab() {
  const [inputText, setInputText] = useState("");
  const { messages, sendMessage, isAsking } = useStore();

  const handleSend = () => {
    const trimmed = inputText.trim();
    if (!trimmed || isAsking) return;
    sendMessage(trimmed);
    setInputText("");
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4 max-w-4xl mx-auto">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${message.isUser ? "justify-end" : "justify-start"}`}
            >
              {!message.isUser && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary text-primary-foreground">
                    <Bot className="h-4 w-4 " />
                  </AvatarFallback>
                </Avatar>
              )}

              <div className={`max-w-[70%] ${message.isUser ? "order-1" : ""}`}>
                <div
                  className={`rounded-lg p-3 ${
                    message.isUser ? "bg-primary text-primary-foreground ml-auto" : "bg-muted "
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
                <p className="text-xs text-muted-foreground mt-1 px-1">{message.timestamp}</p>
              </div>

              {message.isUser && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-secondary text-secondary-foreground">
                    <User className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
              )}
            </div>
          ))}

          {isAsking && (
            <div className="flex gap-3 justify-start">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary text-primary-foreground">
                  <Bot className="h-4 w-4" />
                </AvatarFallback>
              </Avatar>
              <div className="max-w-[70%]">
                <div className="rounded-lg p-3 bg-muted ">
                  <p className="whitespace-pre-wrap">Thinking…</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t border-border p-4 bg-card">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <Textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about your documents..."
                className="min-h-[60px] max-h-32 resize-none "
                rows={2}
                disabled={isAsking}
              />
            </div>
            <Button
              onClick={handleSend}
              disabled={!inputText.trim() || isAsking}
              size="icon"
              className="h-[60px] w-[60px] rounded-lg"
            >
              <Send className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
