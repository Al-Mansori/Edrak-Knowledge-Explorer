import { useState } from "react";
import { Send, Bot, User, BarChart3, FileText, MessageSquare } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ScrollArea } from "./ui/scroll-area";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";

interface Message {
  id: number;
  content: string;
  isUser: boolean;
  timestamp: string;
}

export function ChatArea() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      content: "Hello! I can help you analyze and discuss your documents. What would you like to know?",
      isUser: false,
      timestamp: "10:30 AM"
    },
    {
      id: 2,
      content: "Can you summarize the key points from the Project Overview document?",
      isUser: true,
      timestamp: "10:31 AM"
    },
    {
      id: 3,
      content: "Based on the Project Overview document, here are the key points:\n\n1. The project aims to build a modern web application\n2. Target completion is Q4 2024\n3. Key stakeholders include the design and engineering teams\n4. Budget allocation is $500K for the initial phase",
      isUser: false,
      timestamp: "10:32 AM"
    }
  ]);
  
  const [inputText, setInputText] = useState("");

  const handleSendMessage = () => {
    if (inputText.trim()) {
      const newMessage: Message = {
        id: messages.length + 1,
        content: inputText,
        isUser: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages([...messages, newMessage]);
      setInputText("");
      
      // Simulate AI response
      setTimeout(() => {
        const aiResponse: Message = {
          id: messages.length + 2,
          content: "I understand your question. Let me analyze the relevant documents and provide you with a detailed response.",
          isUser: false,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, aiResponse]);
      }, 1000);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background">
      {/* Tabs Section */}
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
              value="analysis" 
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent flex items-center gap-2"
            >
              <BarChart3 className="h-4 w-4" />
              Analysis
            </TabsTrigger>
            <TabsTrigger 
              value="summary" 
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent flex items-center gap-2"
            >
              <FileText className="h-4 w-4" />
              Summary
            </TabsTrigger>
          </TabsList>

          {/* Chat Tab Content */}
          <TabsContent value="chat" className="flex-1 flex flex-col mt-0">
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4 max-w-4xl mx-auto">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${message.isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    {!message.isUser && (
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-primary text-primary-foreground">
                          <Bot className="h-4 w-4" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                    
                    <div className={`max-w-[70%] ${message.isUser ? 'order-1' : ''}`}>
                      <div
                        className={`rounded-lg p-3 ${
                          message.isUser
                            ? 'bg-primary text-primary-foreground ml-auto'
                            : 'bg-muted'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 px-1">
                        {message.timestamp}
                      </p>
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
              </div>
            </ScrollArea>

            {/* Input Area for Chat */}
            <div className="border-t border-border p-4 bg-card">
              <div className="max-w-4xl mx-auto">
                <div className="flex gap-3 items-end">
                  <div className="flex-1">
                    <Textarea
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Ask a question about your documents..."
                      className="min-h-[60px] max-h-32 resize-none"
                      rows={2}
                    />
                  </div>
                  <Button
                    onClick={handleSendMessage}
                    disabled={!inputText.trim()}
                    size="icon"
                    className="h-[60px] w-[60px] rounded-lg"
                  >
                    <Send className="h-5 w-5" />
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Analysis Tab Content */}
          <TabsContent value="analysis" className="flex-1 mt-0">
            <ScrollArea className="h-full">
              <div className="p-6 max-w-4xl mx-auto">
                <div className="grid gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="h-5 w-5" />
                        Document Analysis Overview
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="text-center p-4 bg-muted rounded-lg">
                          <div className="text-2xl font-bold text-primary">8</div>
                          <div className="text-sm text-muted-foreground">Total Documents</div>
                        </div>
                        <div className="text-center p-4 bg-muted rounded-lg">
                          <div className="text-2xl font-bold text-primary">156</div>
                          <div className="text-sm text-muted-foreground">Pages Analyzed</div>
                        </div>
                        <div className="text-center p-4 bg-muted rounded-lg">
                          <div className="text-2xl font-bold text-primary">4.2MB</div>
                          <div className="text-sm text-muted-foreground">Total Size</div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Content Categories</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-3">
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Technical Documentation</span>
                            <span>45%</span>
                          </div>
                          <Progress value={45} className="h-2" />
                        </div>
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Project Planning</span>
                            <span>30%</span>
                          </div>
                          <Progress value={30} className="h-2" />
                        </div>
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Design Assets</span>
                            <span>25%</span>
                          </div>
                          <Progress value={25} className="h-2" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Key Topics Identified</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {["React Development", "UI/UX Design", "API Integration", "Project Management", "User Research", "Technical Architecture"].map((topic) => (
                          <span key={topic} className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm">
                            {topic}
                          </span>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Summary Tab Content */}
          <TabsContent value="summary" className="flex-1 mt-0">
            <ScrollArea className="h-full">
              <div className="p-6 max-w-4xl mx-auto">
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5" />
                        Executive Summary
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-muted-foreground leading-relaxed">
                        Your document collection contains comprehensive project documentation for a modern web application development initiative. 
                        The materials span technical requirements, design guidelines, user research findings, and project management resources. 
                        Key focus areas include React-based frontend development, API integration strategies, and user experience optimization.
                      </p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Key Findings</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="border-l-4 border-primary pl-4">
                        <h4 className="font-medium">Project Scope</h4>
                        <p className="text-sm text-muted-foreground">Full-stack web application with React frontend and modern API backend, targeting Q4 2024 completion.</p>
                      </div>
                      <div className="border-l-4 border-primary pl-4">
                        <h4 className="font-medium">Technical Stack</h4>
                        <p className="text-sm text-muted-foreground">React, TypeScript, modern UI frameworks, RESTful APIs, and cloud deployment infrastructure.</p>
                      </div>
                      <div className="border-l-4 border-primary pl-4">
                        <h4 className="font-medium">Budget Allocation</h4>
                        <p className="text-sm text-muted-foreground">$500K initial phase budget with clear milestone-based delivery schedule.</p>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Action Items</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        <li className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-primary rounded-full"></div>
                          <span className="text-sm">Finalize technical architecture based on requirements document</span>
                        </li>
                        <li className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-primary rounded-full"></div>
                          <span className="text-sm">Implement design system components from style guide</span>
                        </li>
                        <li className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-primary rounded-full"></div>
                          <span className="text-sm">Conduct user testing sessions based on research findings</span>
                        </li>
                        <li className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-primary rounded-full"></div>
                          <span className="text-sm">Set up development environment and CI/CD pipeline</span>
                        </li>
                      </ul>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}