from app.rag.text import looks_persian, normalize_persian, search_tokens


def test_normalize_persian_unifies_arabic_characters():
    assert normalize_persian("يک  متنِ\r\nفارسی") == "یک متن\nفارسی"


def test_search_tokens_are_unique_and_normalized():
    assert search_tokens("شبکه شبكه و شبکه پایدار") == ["شبکه", "پایدار"]


def test_language_detection():
    assert looks_persian("این یک پرسش فارسی است")
    assert not looks_persian("This is an English question")
