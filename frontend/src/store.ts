// src/store.ts
import { create } from "zustand";
import type {Document} from "./api"
import { askQuestion, type AskExtra } from "./api";
import type { Message } from "./types/chat";

export interface User {
  id: string;
  name: string;
}

export interface Graph {
  nodes: any[];
  links: any[];
}


interface StoreState {
  user: User | null;
  setUser: (user: User | null) => void;

  selectedDoc: Document | null;
  setSelectedDoc: (doc: Document | null) => void;

  graph: Graph | null;
  setGraph: (graph: Graph | null) => void;

  // chat
  messages: Message[];
  isAsking: boolean;
  chatError: string | null;
  clearChat: () => void;
  sendMessage: (text: string) => Promise<void>;


  answer: string | null;
  setAnswer: (answer: string | null) => void;
}
function nowHHMM() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export const useStore = create<StoreState>((set, get) => ({
  user: null,
  setUser: (user) => set({ user }),

  selectedDoc: null,
  setSelectedDoc: (doc) => set({ selectedDoc: doc }),

  graph: null,
  setGraph: (graph) => set({ graph }),

  // chat: start with a friendly assistant message
  messages: [
    {
      id: 1,
      content: "Hello! I can help you analyze and discuss your documents. What would you like to know?",
      isUser: false,
      timestamp: nowHHMM(),
    },
  ],
  isAsking: false,
  chatError: null,
  clearChat: () => set({ messages: [], chatError: null }),

  sendMessage: async (text: string) => {
    const { messages, selectedDoc } = get();

    // push user message
    const userMsg: Message = {
      id: (messages.at(-1)?.id ?? 0) + 1,
      content: text,
      isUser: true,
      timestamp: nowHHMM(),
    };
    set({ messages: [...messages, userMsg], isAsking: true, chatError: null });

    try {
      const extra: AskExtra = {};
      // OPTIONAL: pass document context to backend if it supports it
      // Comment out if your /qa doesn't accept these keys
      if (selectedDoc?.id) extra.doc_id = selectedDoc.id;
      if (selectedDoc?.summary_filename) extra.summary_filename = selectedDoc.summary_filename;

      const res = await askQuestion(text, extra);

      const answer = res?.answer || "I couldn't find an answer.";
      const aiMsg: Message = {
        id: userMsg.id + 1,
        content: answer,
        isUser: false,
        timestamp: nowHHMM(),
        // you can stash sources if your Message type supports it:
        // sources: res?.sources ?? [],
      };

      set({ messages: [...get().messages, aiMsg], isAsking: false });
    } catch (e: any) {
      set({
        isAsking: false,
        chatError: String(e?.message || e),
        messages: [
          ...get().messages,
          {
            id: (get().messages.at(-1)?.id ?? 0) + 1,
            content: `Error: ${String(e?.message || e)}`,
            isUser: false,
            timestamp: nowHHMM(),
          },
        ],
      });
    }
  },

  // (kept for other tabs if used)
  answer: null,
  setAnswer: (answer) => set({ answer }),
}));
