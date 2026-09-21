from __future__ import annotations

from pathlib import Path

from app.rag.types import PageText


class UnsupportedDocumentError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


def load_document(path: Path) -> list[PageText]:
    extension = path.suffix.lower()
    if extension == ".pdf":
        pages = _load_pdf(path)
    elif extension == ".docx":
        pages = _load_docx(path)
    elif extension in {".txt", ".md"}:
        pages = _load_text(path)
    else:
        raise UnsupportedDocumentError(f"Unsupported extension: {extension}")

    if not any(page.text.strip() for page in pages):
        raise EmptyDocumentError(
            "No extractable text was found. Scanned PDFs need OCR before upload."
        )
    return pages


def _load_pdf(path: Path) -> list[PageText]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return [
        PageText(text=page.extract_text() or "", page_number=index)
        for index, page in enumerate(reader.pages, start=1)
    ]


def _load_docx(path: Path) -> list[PageText]:
    from docx import Document

    document = Document(str(path))
    blocks: list[str] = []
    current_heading: str | None = None
    pages: list[PageText] = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = paragraph.style.name.lower() if paragraph.style else ""
        if style.startswith("heading"):
            if blocks:
                pages.append(PageText(text="\n".join(blocks), heading=current_heading))
                blocks = []
            current_heading = text
        else:
            blocks.append(text)

    if blocks or current_heading:
        pages.append(PageText(text="\n".join(blocks), heading=current_heading))
    return pages


def _load_text(path: Path) -> list[PageText]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "windows-1256"):
        try:
            return [PageText(text=raw.decode(encoding))]
        except UnicodeDecodeError:
            continue
    raise ValueError("The text file encoding could not be detected.")
