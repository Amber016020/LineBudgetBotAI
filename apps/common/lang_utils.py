def detect_lang_by_text(text: str) -> str:
    """Detect language: return zh-TW if text contains Chinese, else en."""
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        return "zh-TW"
    return "en"
