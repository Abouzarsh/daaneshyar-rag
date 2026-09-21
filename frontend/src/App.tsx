import { useCallback, useEffect, useRef, useState } from "react";
import { AboutView } from "./components/AboutView";
import { ChatView } from "./components/ChatView";
import { DocumentsView } from "./components/DocumentsView";
import { Sidebar } from "./components/Sidebar";
import { Toasts, type ToastData } from "./components/Toast";
import { Topbar } from "./components/Topbar";
import {
  deleteConversation,
  deleteDocument,
  getConversation,
  getConversations,
  getDocuments,
  getHealth,
  getStats,
  streamChat,
  uploadDocuments,
} from "./lib/api";
import type {
  AppStats,
  ChatMessage,
  ConversationSummary,
  HealthStatus,
  KnowledgeDocument,
  ViewName,
} from "./types";

const emptyStats: AppStats = {
  document_count: 0,
  chunk_count: 0,
  conversation_count: 0,
  question_count: 0,
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "خطای پیش‌بینی‌نشده";
}

export default function App() {
  const [view, setView] = useState<ViewName>("chat");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    null,
  );
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [stats, setStats] = useState<AppStats>(emptyStats);
  const [streaming, setStreaming] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [dark, setDark] = useState(
    () => localStorage.getItem("daaneshyar-theme") !== "light",
  );
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const pushToast = useCallback(
    (message: string, tone: ToastData["tone"] = "success") => {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      setToasts((current) => [...current, { id, message, tone }]);
      window.setTimeout(
        () => setToasts((current) => current.filter((item) => item.id !== id)),
        4200,
      );
    },
    [],
  );

  const refreshDocuments = useCallback(async () => {
    const nextDocuments = await getDocuments();
    setDocuments(nextDocuments);
    setSelectedDocumentIds((current) =>
      current.filter((id) =>
        nextDocuments.some(
          (document) => document.id === id && document.status === "ready",
        ),
      ),
    );
  }, []);

  const refreshSidebar = useCallback(async () => {
    const [nextConversations, nextStats] = await Promise.all([
      getConversations(),
      getStats(),
    ]);
    setConversations(nextConversations);
    setStats(nextStats);
  }, []);

  useEffect(() => {
    Promise.allSettled([
      refreshDocuments(),
      refreshSidebar(),
      getHealth().then(setHealth),
    ]).then((results) => {
      if (results.every((result) => result.status === "rejected")) {
        pushToast("ارتباط با سرویس برقرار نشد", "error");
      }
    });
  }, [pushToast, refreshDocuments, refreshSidebar]);

  useEffect(() => {
    const hasPending = documents.some(
      (document) =>
        document.status === "queued" || document.status === "indexing",
    );
    if (!hasPending) return;
    const timer = window.setInterval(() => {
      refreshDocuments().catch(() => undefined);
      getStats().then(setStats).catch(() => undefined);
    }, 1800);
    return () => window.clearInterval(timer);
  }, [documents, refreshDocuments]);

  const chooseConversation = async (id: string) => {
    if (streaming) return;
    try {
      const conversation = await getConversation(id);
      setActiveConversationId(id);
      setMessages(conversation.messages);
      setView("chat");
    } catch (error) {
      pushToast(errorMessage(error), "error");
    }
  };

  const newChat = () => {
    abortRef.current?.abort();
    setStreaming(false);
    setActiveConversationId(null);
    setMessages([]);
    setView("chat");
    setMobileMenu(false);
  };

  const sendQuestion = async (question: string) => {
    if (streaming) return;
    const stamp = Date.now();
    const userId = "local-user-" + stamp;
    const assistantId = "local-assistant-" + stamp;
    const now = new Date().toISOString();
    setMessages((current) => [
      ...current,
      {
        id: userId,
        role: "user",
        content: question,
        citations: [],
        created_at: now,
      },
      {
        id: assistantId,
        role: "assistant",
        content: "",
        citations: [],
        created_at: now,
        pending: true,
      },
    ]);
    setStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;
    let streamFailed = false;

    try {
      await streamChat(
        {
          question,
          conversation_id: activeConversationId || undefined,
          document_ids: selectedDocumentIds.length
            ? selectedDocumentIds
            : undefined,
        },
        {
          onMeta: (meta) => {
            setActiveConversationId(meta.conversation_id);
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? { ...message, citations: meta.sources }
                  : message,
              ),
            );
          },
          onToken: (content) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      content: message.content + content,
                    }
                  : message,
              ),
            );
          },
          onDone: (data) => {
            setActiveConversationId(data.conversation_id);
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? { ...message, id: data.message_id, pending: false }
                  : message,
              ),
            );
          },
          onError: (message) => {
            streamFailed = true;
            setMessages((current) =>
              current.map((item) =>
                item.id === assistantId
                  ? {
                      ...item,
                      pending: false,
                      content:
                        item.content ||
                        "پاسخ کامل نشد. تنظیمات مدل زبانی را بررسی کنید.",
                    }
                  : item,
              ),
            );
            pushToast(message, "error");
          },
        },
        controller.signal,
      );
    } catch (error) {
      if (controller.signal.aborted) {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId
              ? {
                  ...item,
                  pending: false,
                  content: item.content || "پاسخ توسط کاربر متوقف شد.",
                }
              : item,
          ),
        );
      } else if (!streamFailed) {
        pushToast(errorMessage(error), "error");
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId
              ? {
                  ...item,
                  pending: false,
                  content: "دریافت پاسخ با مشکل روبه‌رو شد.",
                }
              : item,
          ),
        );
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      refreshSidebar().catch(() => undefined);
    }
  };

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    try {
      const results = await uploadDocuments(files);
      const queued = results.filter((item) => item.status === "queued").length;
      const duplicates = results.filter(
        (item) => item.status === "duplicate",
      ).length;
      const rejected = results.filter(
        (item) => item.status === "rejected",
      ).length;
      if (queued) {
        pushToast(
          queued.toLocaleString("fa-IR") + " فایل وارد صف پردازش شد",
        );
      }
      if (duplicates) {
        pushToast("فایل تکراری دوباره اضافه نشد", "error");
      }
      if (rejected) {
        const first = results.find((item) => item.status === "rejected");
        pushToast(first?.detail || "فرمت فایل پذیرفته نشد", "error");
      }
      await refreshDocuments();
    } catch (error) {
      pushToast(errorMessage(error), "error");
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (id: string) => {
    const document = documents.find((item) => item.id === id);
    if (!window.confirm("فایل «" + (document?.name || "") + "» حذف شود؟")) {
      return;
    }
    try {
      await deleteDocument(id);
      await Promise.all([refreshDocuments(), refreshSidebar()]);
      pushToast("سند از پایگاه دانش حذف شد");
    } catch (error) {
      pushToast(errorMessage(error), "error");
    }
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await deleteConversation(id);
      if (activeConversationId === id) newChat();
      await refreshSidebar();
      pushToast("گفت‌وگو حذف شد");
    } catch (error) {
      pushToast(errorMessage(error), "error");
    }
  };

  const toggleTheme = () => {
    setDark((current) => {
      const next = !current;
      localStorage.setItem("daaneshyar-theme", next ? "dark" : "light");
      return next;
    });
  };

  return (
    <div className={"app-shell " + (dark ? "theme-dark" : "theme-light")}>
      <Sidebar
        view={view}
        conversations={conversations}
        activeConversationId={activeConversationId}
        health={health}
        mobileOpen={mobileMenu}
        onClose={() => setMobileMenu(false)}
        onViewChange={setView}
        onSelectConversation={chooseConversation}
        onDeleteConversation={handleDeleteConversation}
        onNewChat={newChat}
      />
      <main className="main-area">
        <Topbar
          view={view}
          health={health}
          dark={dark}
          onToggleTheme={toggleTheme}
          onOpenMenu={() => setMobileMenu(true)}
        />
        <div className="view-container">
          {view === "chat" && (
            <ChatView
              messages={messages}
              documents={documents}
              selectedDocumentIds={selectedDocumentIds}
              streaming={streaming}
              onSelectionChange={setSelectedDocumentIds}
              onSend={sendQuestion}
              onStop={() => abortRef.current?.abort()}
              onOpenDocuments={() => setView("documents")}
            />
          )}
          {view === "documents" && (
            <DocumentsView
              documents={documents}
              stats={stats}
              uploading={uploading}
              onUpload={handleUpload}
              onDelete={handleDeleteDocument}
            />
          )}
          {view === "about" && <AboutView />}
        </div>
      </main>
      <Toasts
        items={toasts}
        onDismiss={(id) =>
          setToasts((current) => current.filter((item) => item.id !== id))
        }
      />
    </div>
  );
}
