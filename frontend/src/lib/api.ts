import type {
  AppStats,
  Conversation,
  ConversationSummary,
  HealthStatus,
  KnowledgeDocument,
  StreamMeta,
  UploadItem,
} from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(API_BASE + path, options);
  if (!response.ok) {
    let detail = "خطا در ارتباط با سرور";
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // Keep the friendly fallback.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function getDocuments(): Promise<KnowledgeDocument[]> {
  return request<KnowledgeDocument[]>("/documents");
}

export function getConversations(): Promise<ConversationSummary[]> {
  return request<ConversationSummary[]>("/conversations");
}

export function getConversation(id: string): Promise<Conversation> {
  return request<Conversation>("/conversations/" + id);
}

export function getStats(): Promise<AppStats> {
  return request<AppStats>("/stats");
}

export function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

export async function uploadDocuments(
  files: File[],
): Promise<UploadItem[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const result = await request<{ items: UploadItem[] }>("/documents", {
    method: "POST",
    body: formData,
  });
  return result.items;
}

export async function deleteDocument(id: string): Promise<void> {
  await request("/documents/" + id, { method: "DELETE" });
}

export async function deleteConversation(id: string): Promise<void> {
  await request("/conversations/" + id, { method: "DELETE" });
}

interface StreamCallbacks {
  onMeta: (data: StreamMeta) => void;
  onToken: (content: string) => void;
  onDone: (data: { conversation_id: string; message_id: string }) => void;
  onError: (message: string) => void;
}

export async function streamChat(
  payload: {
    question: string;
    conversation_id?: string;
    document_ids?: string[];
  },
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(API_BASE + "/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok) {
    let detail = "ارسال پرسش ناموفق بود";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // Keep fallback.
    }
    throw new Error(detail);
  }
  if (!response.body) {
    throw new Error("مرورگر از پاسخ جریانی پشتیبانی نمی‌کند");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || "";

    for (const block of blocks) {
      let event = "message";
      const dataLines: string[] = [];
      for (const line of block.split(/\r?\n/)) {
        if (line.startsWith("event:")) {
          event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }
      if (!dataLines.length) continue;
      const data = JSON.parse(dataLines.join("\n"));
      if (event === "meta") callbacks.onMeta(data as StreamMeta);
      if (event === "token") callbacks.onToken(data.content || "");
      if (event === "done") callbacks.onDone(data);
      if (event === "error") callbacks.onError(data.message || "خطای نامشخص");
    }
    if (done) break;
  }
}
