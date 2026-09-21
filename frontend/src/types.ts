export type DocumentStatus = "queued" | "indexing" | "ready" | "failed";

export interface KnowledgeDocument {
  id: string;
  name: string;
  mime_type: string | null;
  size_bytes: number;
  status: DocumentStatus;
  chunk_count: number;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  index: number;
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number | null;
  excerpt: string;
  score: number;
  retrieval_methods: string[];
}

export interface ChatMessage {
  id: string;
  conversation_id?: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
  pending?: boolean;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface AppStats {
  document_count: number;
  chunk_count: number;
  conversation_count: number;
  question_count: number;
}

export interface HealthComponent {
  ok: boolean;
  provider?: string;
  backend?: string;
  model?: string;
  detail?: string;
}

export interface HealthStatus {
  status: "ok" | "degraded";
  version: string;
  components: Record<string, HealthComponent>;
}

export interface UploadItem {
  document: KnowledgeDocument | null;
  filename: string;
  status: "queued" | "duplicate" | "rejected";
  detail: string | null;
  duplicate_of: string | null;
}

export interface StreamMeta {
  conversation_id: string;
  message_id: string;
  sources: Citation[];
  retrieval_ms: number;
  model: string;
}

export type ViewName = "chat" | "documents" | "about";
