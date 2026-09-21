import {
  AlertCircle,
  CheckCircle2,
  File,
  FileText,
  Layers3,
  LoaderCircle,
  Search,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import type { AppStats, KnowledgeDocument } from "../types";

interface DocumentsViewProps {
  documents: KnowledgeDocument[];
  stats: AppStats;
  uploading: boolean;
  onUpload: (files: File[]) => void;
  onDelete: (id: string) => void;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("fa-IR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

const statusCopy = {
  queued: { label: "در صف پردازش", icon: LoaderCircle },
  indexing: { label: "در حال نمایه‌سازی", icon: LoaderCircle },
  ready: { label: "آماده پرسش", icon: CheckCircle2 },
  failed: { label: "پردازش ناموفق", icon: AlertCircle },
};

export function DocumentsView({
  documents,
  stats,
  uploading,
  onUpload,
  onDelete,
}: DocumentsViewProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () =>
      documents.filter((document) =>
        document.name.toLowerCase().includes(query.toLowerCase()),
      ),
    [documents, query],
  );

  const acceptFiles = (files: FileList | null) => {
    if (!files?.length) return;
    onUpload(Array.from(files));
  };

  return (
    <section className="page-view documents-view">
      <header className="page-heading">
        <div>
          <span className="eyebrow">پایگاه دانش</span>
          <h1>کتابخانه اسناد</h1>
          <p>فایل‌ها را مدیریت کن و وضعیت پردازش هر سند را ببین.</p>
        </div>
      </header>

      <div className="stats-grid">
        <article className="stat-card">
          <span className="stat-icon gold"><FileText size={21} /></span>
          <div><strong>{stats.document_count.toLocaleString("fa-IR")}</strong><small>سند آماده</small></div>
        </article>
        <article className="stat-card">
          <span className="stat-icon teal"><Layers3 size={21} /></span>
          <div><strong>{stats.chunk_count.toLocaleString("fa-IR")}</strong><small>قطعه دانشی</small></div>
        </article>
        <article className="stat-card">
          <span className="stat-icon violet"><Search size={21} /></span>
          <div><strong>{stats.question_count.toLocaleString("fa-IR")}</strong><small>پرسش پاسخ‌داده‌شده</small></div>
        </article>
      </div>

      <div
        className={"upload-zone " + (dragging ? "dragging" : "")}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          acceptFiles(event.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Enter") inputRef.current?.click();
        }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md"
          onChange={(event) => {
            acceptFiles(event.target.files);
            event.target.value = "";
          }}
        />
        <span className="upload-icon">
          {uploading ? (
            <LoaderCircle className="spin" size={28} />
          ) : (
            <UploadCloud size={28} />
          )}
        </span>
        <div>
          <strong>
            {uploading ? "در حال ارسال فایل…" : "فایل را اینجا رها کن"}
          </strong>
          <p>یا برای انتخاب از سیستم کلیک کن</p>
        </div>
        <small>PDF، DOCX، TXT و MD · حداکثر ۲۵ مگابایت</small>
      </div>

      <div className="document-panel">
        <div className="document-panel-head">
          <div>
            <h2>همه فایل‌ها</h2>
            <span>{documents.length.toLocaleString("fa-IR")} مورد</span>
          </div>
          <label className="search-field">
            <Search size={17} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="جست‌وجوی نام فایل"
            />
          </label>
        </div>

        {filtered.length === 0 ? (
          <div className="document-empty">
            <File size={36} />
            <strong>
              {query ? "فایلی با این نام پیدا نشد" : "کتابخانه هنوز خالی است"}
            </strong>
            <p>برای شروع، یکی از اسناد نمونه یا فایل خودت را اضافه کن.</p>
          </div>
        ) : (
          <div className="document-list">
            {filtered.map((document) => {
              const status = statusCopy[document.status];
              const StatusIcon = status.icon;
              return (
                <article className="document-row" key={document.id}>
                  <span className="file-badge">
                    {document.name.split(".").pop()?.toUpperCase()}
                  </span>
                  <div className="document-info">
                    <strong title={document.name}>{document.name}</strong>
                    <small>
                      {formatBytes(document.size_bytes)}
                      <i>·</i>
                      {formatDate(document.created_at)}
                      {document.chunk_count > 0 && (
                        <>
                          <i>·</i>
                          {document.chunk_count.toLocaleString("fa-IR")} قطعه
                        </>
                      )}
                    </small>
                    {document.error && (
                      <span className="document-error">{document.error}</span>
                    )}
                  </div>
                  <span className={"document-status " + document.status}>
                    <StatusIcon
                      size={15}
                      className={
                        document.status === "indexing" ||
                        document.status === "queued"
                          ? "spin"
                          : ""
                      }
                    />
                    {status.label}
                  </span>
                  <button
                    className="icon-button danger"
                    onClick={() => onDelete(document.id)}
                    aria-label={"حذف " + document.name}
                  >
                    <Trash2 size={17} />
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
