# 🚀 Edrak Knowledge Explorer

A full-stack AI-powered platform for **document understanding**, **knowledge graph visualization**, and **intelligent chat interaction** — built with **FastAPI**, **LlamaIndex**, and a **React + Tailwind + shadcn/ui** frontend.

![Edrak Eemo](demo.gif)

---

## 📘 Overview

Edrak Knowledge Explorer enables users to **upload, analyze, and explore documents** interactively.
It combines **retrieval-augmented generation (RAG)**, **knowledge graph indexing**, and a **chat assistant** that answers questions based on your data.

---

## ⚙️ Features

* 🧠 **Knowledge Engine (Backend)**

  * Built with **FastAPI** + **LlamaIndex**
  * Summarizes markdowns and builds **Knowledge Graphs** (`kg_index.get_networkx_graph`)
  * Exposes REST APIs for querying, summarization, and graph retrieval

* 💬 **Interactive Chat Interface (Frontend)**

  * Built with **React + TypeScript + TailwindCSS + shadcn/ui**
  * Multi-tab view: **Chat**, **Graph**, **Summary**, **PDF**
  * Real-time visualization using **react-force-graph-2d**

* 📈 **Knowledge Graph Visualization**

  * Dynamically rendered relationships between entities
  * Zoom, drag, and hover tooltips

* ⚡ **AI-Powered Summarization**

  * Uses **Google Gemini via LlamaIndex** for summarizing documents

---

## 🧩 Project Structure

```
.
├── backend/
│   ├── main.py
│   ├── kg_endpoints.py
│   ├── summarize.py
│   ├── api/
│   └── publications_dataset/
│       ├── markdown/
│       ├── summary/
│       └── images/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── store/
│   │   └── api.ts
│   └── package.json
│
└── README.md
```

---

## 🚀 Getting Started

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Al-Mansori/Edrak-Knowledge-Explorer.git
cd edrak
```

### 2️⃣ Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload
```

### 3️⃣ Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🧠 API Endpoints (Markdown Style)

### **Documents**

```http
GET /documents/                 # List all documents
GET /documents/{id}/summary     # Get summary
GET /documents/{id}/graph       # Get knowledge graph data
```

### **Knowledge Graph**

```http
GET /kg/build                   # Build or load graph index
GET /kg/graph                   # Return graph JSON (for frontend)
```

### **Chat / Query**

```http
POST /query                     # Ask questions to the knowledge engine
```

---

## 🧰 Tech Stack

| Layer        | Tools                                                           |
| ------------ | --------------------------------------------------------------- |
| **Frontend** | React, TypeScript, TailwindCSS, shadcn/ui, react-force-graph-2d |
| **Backend**  | FastAPI, LlamaIndex, Google Gemini                              |
| **AI / ML**  | Retrieval-Augmented Generation (RAG), Knowledge Graph Index     |
| **Data**     | Markdown-based document storage & summaries                     |

---

## 🤖 Use of Artificial Intelligence

AI is used for:

* Document summarization using **Google Gemini**
* Entity extraction and relation mapping using **LlamaIndex KnowledgeGraphIndex**
* Contextual question answering through **RAG pipelines**



