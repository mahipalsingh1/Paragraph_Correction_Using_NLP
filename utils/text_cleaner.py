# utils/text_cleaner.py
import re

# Basic unicode punctuation normalization maps
QUOTE_MAP = {
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
}
DASH_MAP = {
    "–": "-", "—": "-", "―": "-",
}

NBSP = "\u00A0"

def _normalize_unicode_punct(t: str) -> str:
    # Normalize non-breaking spaces first
    t = t.replace(NBSP, " ")
    # quotes
    for k, v in QUOTE_MAP.items():
        t = t.replace(k, v)
    # dashes (keep hyphen-minus for tokenization with [A-Za-z\-'])
    for k, v in DASH_MAP.items():
        t = t.replace(k, v)
    return t

def _fix_spaces_around_punct(t: str) -> str:
    # Remove spaces before .,!?;: and closing quotes/brackets
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"\s+([\)\]\}])", r"\1", t)

    # Ensure a space after punctuation if followed by a word (avoid 3.14 type numbers)
    t = re.sub(r"([,;:!?])([A-Za-z])", r"\1 \2", t)

    # Spaces around standalone dashes used as separators:
    # only when dash is not part of a hyphenated word on either side
    t = re.sub(r"(?<![A-Za-z0-9])-(?![A-Za-z0-9])", " - ", t)  # isolated dash
    t = re.sub(r"\s*-\s*", " - ", t)                           # normalize surrounding spaces
    # But collapse back when it's clearly a hyphenated word segment
    t = re.sub(r"\b\s*-\s*\b", "-", t)

    # Collapse extra spaces again
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def _collapse_repeated_punct(t: str) -> str:
    # Reduce multiple exclamations/question marks/periods to one
    t = re.sub(r"([.!?])\1{1,}", r"\1", t)
    # Reduce multiple commas
    t = re.sub(r"(,)\1{1,}", r"\1", t)
    return t

def clean_text(text: str) -> str:
    """
    Lightweight, conservative cleaning:
    - Trim and collapse whitespace (incl. non-breaking spaces)
    - Normalize curly quotes/dashes to ASCII
    - Tidy spaces around punctuation (without breaking hyphenated words)
    - Collapse repeated punctuation
    Does NOT lowercase or alter words.
    """
    if text is None:
        return ""
    t = str(text).strip()
    t = _normalize_unicode_punct(t)
    t = re.sub(r"\s+\n", "\n", t)       # trim trailing spaces before newlines
    t = re.sub(r"\n{3,}", "\n\n", t)    # limit excessive blank lines
    t = re.sub(r"[ \t]+", " ", t)       # collapse runs of spaces/tabs
    t = _collapse_repeated_punct(t)
    t = _fix_spaces_around_punct(t)
    return t
