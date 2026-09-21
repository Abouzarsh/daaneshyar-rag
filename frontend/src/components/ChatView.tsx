import {
  ArrowLeft,
  BookOpenCheck,
  FileSearch,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect, useRef } from "react";
import type { ChatMessage, KnowledgeDocument } from "../types";
import { Composer } from "./Composer";
import { LogoMark } from "./LogoMark";
import { MessageBubble } from "./MessageBubble";

interface ChatViewProps {
  messages: ChatMessage[];
  documents: KnowledgeDocument[];
  selectedDocumentIds: string[];
  streaming: boolean;
  onSelectionChange: (ids: string[]) => void;
  onSend: (question: string) => void;
  onStop: () => void;
  onOpenDocuments: () => void;
}

const suggestions = [
  {
    icon: FileSearch,
    title: "یک خلاصه مدیریتی بده",
    prompt: "از محتوای اسناد یک خلاصه مدیریتی کوتاه و دقیق تهیه کن.",
  },
  {
    icon: ShieldCheck,
    title: "ریسک‌ها را پیدا کن",
    prompt: "مهم‌ترین ریسک‌ها، محدودیت‌ها و نکات احتیاطی اسناد چیست؟",
  },
  {
    icon: BookOpenCheck,
    title: "نکات کلیدی را فهرست کن",
    prompt: "نکات کلیدی اسناد را با ذکر منبع و شماره صفحه فهرست کن.",
  },
];

export function ChatView({
  messages,
  documents,
  selectedDocumentIds,
  streaming,
  onSelectionChange,
  onSend,
  onStop,
  onOpenDocuments,
}: ChatViewProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const readyCount = documents.filter((item) => item.status === "ready").length;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <section className="chat-view">
      <div className="chat-scroll">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="empty-logo">
              <LogoMark size={64} />
            </div>
            <div className="eyebrow">
              <Sparkles size={15} />
              <span>پاسخ مستند، نه حدس مدل</span>
            </div>
            <h1>
              هر سؤال، یک پاسخ
              <br />
              <em>قابل پیگیری</em>
            </h1>
            <p>
              اسنادت را اضافه کن و جواب دقیق را همراه با نام فایل، شماره صفحه
              و متن شاهد بگیر.
            </p>

            {readyCount > 0 ? (
              <div className="suggestion-grid">
                {suggestions.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.title}
                      className="suggestion-card"
                      onClick={() => onSend(item.prompt)}
                    >
                      <Icon size={20} />
                      <span>{item.title}</span>
                      <ArrowLeft size={16} />
                    </button>
                  );
                })}
              </div>
            ) : (
              <button className="empty-upload-cta" onClick={onOpenDocuments}>
                افزودن اولین سند
                <ArrowLeft size={18} />
              </button>
            )}
          </div>
        ) : (
          <div className="messages">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <Composer
        documents={documents}
        selectedDocumentIds={selectedDocumentIds}
        streaming={streaming}
        disabled={readyCount === 0}
        onSelectionChange={onSelectionChange}
        onSend={onSend}
        onStop={onStop}
      />
    </section>
  );
}
