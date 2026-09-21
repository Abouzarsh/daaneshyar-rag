from app.rag.chunker import TextChunker
from app.rag.types import PageText


def test_chunker_preserves_page_and_overlap():
    words = [f"واژه{i}" for i in range(130)]
    text = " ".join(words[:65]) + ". " + " ".join(words[65:])
    chunker = TextChunker(chunk_size_words=80, overlap_words=10)

    chunks = chunker.split("doc-1", [PageText(text=text, page_number=4)])

    assert len(chunks) == 2
    assert chunks[0].page_number == 4
    assert chunks[1].page_number == 4
    assert chunks[0].content.split()[-10:] == chunks[1].content.split()[:10]
    assert chunks[0].id != chunks[1].id


def test_chunk_ids_are_deterministic():
    chunker = TextChunker(chunk_size_words=80, overlap_words=10)
    pages = [PageText(text="متن کوتاه برای یک قطعه آزمایشی.")]
    first = chunker.split("same-doc", pages)
    second = chunker.split("same-doc", pages)
    assert first[0].id == second[0].id
