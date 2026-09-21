import {
  ArrowUp,
  Check,
  Files,
  LoaderCircle,
  Square,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { KnowledgeDocument } from "../types";

interface ComposerProps {
  documents: KnowledgeDocument[];
  selectedDocumentIds: string[];
  streaming: boolean;
  disabled?: boolean;
  onSelectionChange: (ids: string[]) => void;
  onSend: (question: string) => void;
  onStop: () => void;
}

export function Composer({
  documents,
  selectedDocumentIds,
  streaming,
  disabled,
  onSelectionChange,
  onSend,
  onStop,
}: ComposerProps) {
  const [question, setQuestion] = useState("");
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const readyDocuments = documents.filter((item) => item.status === "ready");

  useEffect(() => {
    const target = textAreaRef.current;
    if (!target) return;
    target.style.height = "auto";
    target.style.height = Math.min(target.scrollHeight, 150) + "px";
  }, [question]);

  const submit = () => {
    const clean = question.trim();
    if (!clean || streaming || disabled) return;
    onSend(clean);
    setQuestion("");
  };

  const toggleDocument = (id: string) => {
    if (selectedDocumentIds.includes(id)) {
      onSelectionChange(
        selectedDocumentIds.filter((documentId) => documentId !== id),
      );
    } else {
      onSelectionChange([...selectedDocumentIds, id]);
    }
  };

  return (
    <div className="composer-wrap">
      <div className="composer">
        <textarea
          ref={textAreaRef}
          value={question}
          placeholder={
            disabled
              ? "ابتدا یک سند به کتابخانه اضافه کنید…"
              : "سؤالت را از میان اسناد بپرس…"
          }
          disabled={disabled}
          rows={1}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
        />
        <div className="composer-toolbar">
          <details className="source-picker">
            <summary>
              <Files size={17} />
              <span>
                {selectedDocumentIds.length
                  ? selectedDocumentIds.length + " سند انتخاب‌شده"
                  : "همه اسناد"}
              </span>
            </summary>
            <div className="source-menu">
              <button
                className={
                  "source-option " +
                  (selectedDocumentIds.length === 0 ? "selected" : "")
                }
                onClick={() => onSelectionChange([])}
              >
                <span>همه اسناد آماده</span>
                {selectedDocumentIds.length === 0 && <Check size={16} />}
              </button>
              {readyDocuments.map((document) => (
                <button
                  key={document.id}
                  className={
                    "source-option " +
                    (selectedDocumentIds.includes(document.id)
                      ? "selected"
                      : "")
                  }
                  onClick={() => toggleDocument(document.id)}
                >
                  <span>{document.name}</span>
                  {selectedDocumentIds.includes(document.id) && (
                    <Check size={16} />
                  )}
                </button>
              ))}
            </div>
          </details>

          {streaming ? (
            <button
              className="send-button stop"
              onClick={onStop}
              aria-label="توقف پاسخ"
            >
              <Square size={16} fill="currentColor" />
            </button>
          ) : (
            <button
              className="send-button"
              onClick={submit}
              disabled={!question.trim() || disabled}
              aria-label="ارسال پرسش"
            >
              {disabled ? (
                <LoaderCircle size={18} />
              ) : (
                <ArrowUp size={20} />
              )}
            </button>
          )}
        </div>
      </div>
      <p className="composer-note">
        پاسخ‌ها از اسناد بازیابی می‌شوند؛ برای تصمیم‌های حساس، منبع را بررسی کنید.
      </p>
    </div>
  );
}
