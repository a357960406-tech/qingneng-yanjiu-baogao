import type { DocumentItem, ReportItem } from "@/lib/types";

const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = (data as { error?: { message?: string } }).error?.message ?? `HTTP ${res.status}`;
    throw new Error(message);
  }
  return data as T;
}

export const api = {
  listDocuments: () => request<{ items: DocumentItem[] }>("/documents"),

  uploadDocument: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<DocumentItem>("/documents", { method: "POST", body: fd });
  },

  listReports: () => request<{ items: ReportItem[] }>("/reports"),

  createReport: (payload: { title: string; target_words: number; user_requirements?: string }) =>
    request<ReportItem>("/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
};
