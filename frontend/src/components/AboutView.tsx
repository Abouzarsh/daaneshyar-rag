import {
  Binary,
  Database,
  FileSearch,
  Github,
  Languages,
  LockKeyhole,
  Network,
  Radio,
} from "lucide-react";

const features = [
  {
    icon: FileSearch,
    title: "بازیابی ترکیبی",
    text: "ترکیب جست‌وجوی معنایی و کلیدواژه‌ای با الگوریتم RRF.",
  },
  {
    icon: Languages,
    title: "فارسی‌محور",
    text: "نرمال‌سازی نویسه‌های فارسی و مدل Embedding چندزبانه.",
  },
  {
    icon: Radio,
    title: "پاسخ جریانی",
    text: "نمایش پاسخ مدل به‌صورت زنده با Server-Sent Events.",
  },
  {
    icon: LockKeyhole,
    title: "محلی و خصوصی",
    text: "اجرای کامل با Ollama؛ سندها لازم نیست از سیستم خارج شوند.",
  },
];

export function AboutView() {
  return (
    <section className="page-view about-view">
      <header className="about-hero">
        <span className="eyebrow">RAG، از صفر تا محصول</span>
        <h1>چرا دانشیار ساخته شد؟</h1>
        <p>
          یک پیاده‌سازی شفاف و قابل توسعه از Retrieval-Augmented Generation؛
          برای زمانی که جواب درست باید به سند درست متصل باشد.
        </p>
      </header>

      <div className="feature-grid">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <article className="feature-card" key={feature.title}>
              <span><Icon size={22} /></span>
              <h2>{feature.title}</h2>
              <p>{feature.text}</p>
            </article>
          );
        })}
      </div>

      <div className="architecture-card">
        <div className="architecture-copy">
          <span className="eyebrow">جریان پاسخ</span>
          <h2>هر پاسخ، از یک مسیر قابل مشاهده می‌گذرد</h2>
          <p>
            متن سند استخراج و قطعه‌بندی می‌شود؛ سپس بازیابی معنایی و
            کلیدواژه‌ای بهترین شواهد را پیدا می‌کنند و مدل فقط با همان شواهد
            پاسخ می‌دهد.
          </p>
        </div>
        <div className="architecture-flow">
          <div><FileSearch size={20} /><span>استخراج سند</span></div>
          <b>←</b>
          <div><Binary size={20} /><span>Embedding</span></div>
          <b>←</b>
          <div><Database size={20} /><span>Qdrant + FTS5</span></div>
          <b>←</b>
          <div><Network size={20} /><span>پاسخ مستند</span></div>
        </div>
      </div>

      <div className="stack-strip">
        <span>FastAPI</span>
        <i />
        <span>React + TypeScript</span>
        <i />
        <span>Qdrant</span>
        <i />
        <span>Ollama</span>
        <i />
        <span>SQLite FTS5</span>
      </div>

      <a
        className="github-link"
        href="https://github.com/Abouzarsh/daaneshyar-rag"
        target="_blank"
        rel="noreferrer"
      >
        <Github size={19} />
        مشاهده کد پروژه در GitHub
      </a>
    </section>
  );
}
