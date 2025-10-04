// api.ts
// Base URL can be set in index.html before loading main.js:
//   <script>window.API_BASE_URL = "https://api.your-host.com";</script>

declare global {
  interface Window {
    API_BASE_URL?: string;
  }
}

const BASE_URL: string = (typeof window !== "undefined" && window.API_BASE_URL) || "http://localhost:8000";

/* -------------------- types -------------------- */

export type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

export interface HttpOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  params?: Record<string, string | number | boolean | null | undefined>;
  body?: Json | Record<string, unknown> | undefined;
  headers?: Record<string, string>;
}

export type HttpBlobOptions = Pick<HttpOptions, "params" | "headers">;

export type ListParams = {
  q?: string;
  skip?: number;
  limit?: number;
};

export type KGDirection = "in" | "out" | "both";

/** ---- Documents ---- */
export interface Document {
  id: string;
  title: string;
  pdf_filename: string;
  content_list_filename: string;
  summary_filename: string;
  pdf_url: string;
  content_list_url: string;
  summary_url: string;
}

/** ---- KG ---- */
export interface NodeLinkGraph {
  nodes: Array<{ id: string; label?: string; group?: string; [k: string]: unknown }>;
  edges: Array<{ source: string; target: string; predicate?: string; weight?: number; [k: string]: unknown }>;
  [k: string]: unknown;
}

export interface Triplet {
  subject: string;
  predicate: string;
  object: string;
  [k: string]: unknown;
}

/* -------------------- internals -------------------- */

function authHeader(): Record<string, string> {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function buildUrl(path: string, params?: Record<string, string | number | boolean | null | undefined>): string {
  const base = BASE_URL.replace(/\/$/, "");
  const url = new URL(base + path);
  if (params && typeof params === "object") {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    });
  }
  return url.toString();
}

async function http<T = unknown>(path: string, { method = "GET", params, body, headers }: HttpOptions = {}): Promise<T> {
  const res = await fetch(buildUrl(path, params), {
    method,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(),
      ...(headers || {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    const msg =
      (data &&
        typeof data === "object" &&
        data !== null &&
        // @ts-expect-error – indexing unknown
        (data.detail || data.message || data.error)) ||
      res.statusText ||
      "Request failed";
    throw new Error(String(msg));
  }
  return data as T;
}

// For binaries like PDFs
async function httpBlob(path: string, { params, headers }: HttpBlobOptions = {}): Promise<Blob> {
  const res = await fetch(buildUrl(path, params), {
    method: "GET",
    headers: { ...authHeader(), ...(headers || {}) },
  });
  if (!res.ok) throw new Error(res.statusText || "Request failed");
  return await res.blob();
}

/* -------------------- 📄 Documents -------------------- */

export function listDocuments(params: ListParams = {}) {
  return http<Document[]>("/documents", { params });
}

export function getDocument<T = Document>(doc_id: string) {
  if (!doc_id) throw new Error("doc_id is required");
  return http<T>(`/documents/${encodeURIComponent(doc_id)}`);
}

/* -------------------- 📑 Files -------------------- */

export async function getPdfBlob(filename: string) {
  if (!filename) throw new Error("filename is required");
  return httpBlob(`/files/${encodeURIComponent(filename)}`);
}

// Convenience: returns an object URL you can plug into <iframe src=...>
export async function getPdfObjectUrl(filename: string) {
  const blob = await getPdfBlob(filename);
  return URL.createObjectURL(blob);
}

export function getContentList<T = unknown>(filename: string) {
  if (!filename) throw new Error("filename is required");
  return http<T>(`/files/${encodeURIComponent(filename)}`);
}

export function getSummary<T = unknown>(filename: string) {
  if (!filename) throw new Error("filename is required");
  return http<T>(`/files/${encodeURIComponent(filename)}`);
}

/* -------------------- ❓ QA -------------------- */

export interface AskExtra {
  [k: string]: Json;
}

export interface AskResponse {
  answer?: string;
  sources?: Array<{ id?: string; title?: string; score?: number; [k: string]: unknown }>;
  [k: string]: unknown;
}

export function askQuestion(question: string, extra: AskExtra = {}) {
  if (!question) throw new Error("question is required");
  return http<AskResponse>("/qa", { method: "POST", body: { question, ...extra } });
}

/* -------------------- 🩺 Health -------------------- */

export function health() {
  return http<{ status: string; [k: string]: unknown }>("/health");
}

/* -------------------- 📊 KG (per-file) -------------------- */

export function kgFileList(params: ListParams = {}) {
  return http<{ filename: string; [k: string]: unknown }[]>("/kg/file/list", { params });
}

export interface KgFileNodeLinkParams {
  file: string;
  [k: string]: string | number | boolean | undefined;
}

export function kgFileNodeLink(params: KgFileNodeLinkParams) {
  return http<NodeLinkGraph>("/kg/file/node-link", { params });
}

export interface KgFileNeighborsParams {
  filename: string;
  node: string;
  direction?: KGDirection;
  limit?: number;
  depth?: number;
  [k: string]: string | number | boolean | undefined;
}

export function kgFileNeighbors(params: KgFileNeighborsParams) {
  return http<string[]>("/kg/file/neighbors", { params });
}

export interface KgFileTripletsParams {
  filename: string;
  subject?: string;
  predicate?: string;
  object?: string;
  limit?: number;
  [k: string]: string | number | boolean | undefined;
}

export function kgFileTriplets(params: KgFileTripletsParams) {
  return http<Triplet[]>("/kg/file/triplets", { params });
}

/* -------------------- 🌐 KG (global) -------------------- */

export function kgNodeLink(params: { q?: string; limit?: number } = {}) {
  return http<NodeLinkGraph>("/kg/node-link", { params });
}

export function kgNeighbors(params: { node: string; direction?: KGDirection; limit?: number; depth?: number }) {
  return http<string[]>("/kg/neighbors", { params });
}

export function kgTriplets(params: { subject?: string; predicate?: string; object?: string; limit?: number }) {
  return http<Triplet[]>("/kg/triplets", { params });
}

export function kgStats() {
  return http<{ nodes?: number; edges?: number; triplets?: number; [k: string]: unknown }>("/kg/stats");
}

/* -------------------- helpers -------------------- */

export async function downloadBlobAs(blob: Blob, filename?: string) {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: filename || "file" });
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
