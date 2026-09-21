# راهنمای انتشار در GitHub

## ۱. شخصی‌سازی کوتاه

پیش از انتشار این موارد را بررسی کنید:

- نام نویسنده در README و backend/pyproject.toml
- آدرس مخزن `https://github.com/Abouzarsh/daaneshyar-rag` پس از ساخت آن
- تصاویر داخل docs/screenshots

هیچ فایل .env، داده واقعی سازمانی یا کلید API را Commit نکنید.

## ۲. ساخت مخزن

در GitHub یک repository عمومی با نام daaneshyar-rag بسازید. گزینه ایجاد README
یا .gitignore را فعال نکنید، چون پروژه این فایل‌ها را دارد.

سپس در پوشه پروژه:

    git init
    git add .
    git commit -m "feat: build the initial Daaneshyar RAG workspace"
    git branch -M main
    git remote add origin https://github.com/Abouzarsh/daaneshyar-rag.git
    git push -u origin main

## ۳. تاریخچه طبیعی‌تر و قابل دفاع

اگر می‌خواهید پروژه را با چند Commit آموزشی منتشر کنید، تغییرها را در این
ترتیب Commit کنید:

1. chore: scaffold backend and web workspace
2. feat: add document extraction and Persian-aware chunking
3. feat: implement hybrid Qdrant and FTS5 retrieval
4. feat: stream grounded Ollama answers with citations
5. feat: build the Persian document workspace UI
6. test: cover ingestion, duplicate detection, and chat flow
7. docs: add architecture, demo, and evaluation notes

تاریخ Commitها را دستکاری نکنید. طبیعی‌بودن پروژه از تصمیم‌های قابل توضیح و
کد منسجم می‌آید، نه از ساختن سابقه جعلی.

## ۴. تنظیمات صفحه GitHub

Description پیشنهادی:

    Persian-first, local RAG workspace with hybrid retrieval, streamed answers, and inspectable citations.

Topics پیشنهادی:

    rag, persian-nlp, fastapi, react, qdrant, ollama, hybrid-search, llm

در بخش Social preview از تصویر docs/social-preview.png استفاده کنید.

## ۵. قبل از اشتراک لینک

    cd backend
    pytest

    cd ../frontend
    npm run build
    npm run lint

سپس لینک مخزن را در یک پنجره ناشناس باز کنید و مطمئن شوید README، تصاویر و
دستور اجرای اولیه درست دیده می‌شوند.
