import hashlib
import html
import re
import unicodedata

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
ORDER_RE = re.compile(r"\b(?:order|ticket|case|invoice)[\s#:.-]*[A-Z0-9-]{4,}\b", re.IGNORECASE)
HTML_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value.replace("\x00", ""))
    text = html.unescape(text)
    text = HTML_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()


def normalized_label(value: str) -> str:
    clean = normalize_text(value)
    return clean[:1].upper() + clean[1:] if clean else clean


def mask_pii(value: str) -> str:
    text = EMAIL_RE.sub("[EMAIL]", value)
    text = PHONE_RE.sub("[PHONE]", text)
    text = URL_RE.sub("[URL]", text)
    return ORDER_RE.sub("[REFERENCE_ID]", text)


def content_hash(value: str) -> str:
    canonical = normalize_text(value).casefold()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
