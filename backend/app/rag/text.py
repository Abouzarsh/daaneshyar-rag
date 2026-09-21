from __future__ import annotations

import re
import unicodedata

_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
    }
)
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")
_CONTROL = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_WHITESPACE = re.compile(r"[ \t\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_TOKEN = re.compile(r"[\w\u0600-\u06ff]+", flags=re.UNICODE)


def normalize_persian(text: str) -> str:
    """Normalize Persian/Arabic variants while keeping paragraph boundaries."""

    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.translate(_ARABIC_TO_PERSIAN)
    normalized = _DIACRITICS.sub("", normalized)
    normalized = _CONTROL.sub("", normalized)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _WHITESPACE.sub(" ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return _BLANK_LINES.sub("\n\n", normalized).strip()


def search_tokens(text: str, *, limit: int = 12) -> list[str]:
    normalized = normalize_persian(text).lower()
    tokens: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN.finditer(normalized):
        token = match.group(0)
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
        if len(tokens) >= limit:
            break
    return tokens


def looks_persian(text: str) -> bool:
    persian_chars = len(re.findall(r"[\u0600-\u06ff]", text))
    latin_chars = len(re.findall(r"[A-Za-z]", text))
    return persian_chars >= latin_chars
