import { Check, Copy, FileText, Sparkles } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../types";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isAssistant = message.role === "assistant";

  const copy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  if (!isAssistant) {
    return (
      <div className="message-row user-message">
        <div className="user-bubble">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="message-row assistant-message">
      <div className="assistant-avatar">
        <Sparkles size={18} />
      </div>
      <div className="assistant-content">
        <div className="assistant-label">
          <span>دانشیار</span>
          {message.pending && <i className="thinking-dot" />}
        </div>
        <div className="markdown-body">
          {message.content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          ) : (
            <div className="typing-indicator" aria-label="در حال پاسخ">
              <span />
              <span />
              <span />
            </div>
          )}
        </div>

        {message.citations.length > 0 && (
          <div className="citations">
            <div className="citations-heading">
              <FileText size={16} />
              <span>{message.citations.length} منبع استفاده‌شده</span>
            </div>
            <div className="citation-grid">
              {message.citations.map((citation) => (
                <details className="citation-card" key={citation.chunk_id}>
                  <summary>
                    <span className="citation-index">{citation.index}</span>
                    <span className="citation-title">
                      <strong>{citation.document_name}</strong>
                      <small>
                        {citation.page_number
                          ? "صفحه " + citation.page_number
                          : "بدون شماره صفحه"}
                        <i>·</i>
                        {citation.retrieval_methods.includes("semantic")
                          ? "معنایی"
                          : "کلیدواژه‌ای"}
                      </small>
                    </span>
                    <span className="citation-score">
                      {Math.round(citation.score * 100)}٪
                    </span>
                  </summary>
                  <p>{citation.excerpt}</p>
                </details>
              ))}
            </div>
          </div>
        )}

        {message.content && !message.pending && (
          <button className="message-action" onClick={copy}>
            {copied ? <Check size={15} /> : <Copy size={15} />}
            {copied ? "کپی شد" : "کپی پاسخ"}
          </button>
        )}
      </div>
    </div>
  );
}
