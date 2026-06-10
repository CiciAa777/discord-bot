"""
sensitive.py — single source of truth for sensitive content detection.
Imported by both ingestion.py and conversation.py so logic never drifts.

Three rules:
  1. Known token prefixes (sk-, ghp_, Bearer, JWT)
  2. Keyword + flexible separator + value that contains at least one digit+letter mix
  3. Standalone 15+ char mixed alphanumeric string (only when text isn't a normal sentence)
"""
import re

# Rule 1: known token prefixes — zero false positives
_EXPLICIT_TOKEN_RE = re.compile(
    r"(sk-[a-zA-Z0-9]{20,}"
    r"|ghp_[a-zA-Z0-9]{36}"
    r"|gho_[a-zA-Z0-9]{36}"
    r"|Bearer\s+[a-zA-Z0-9\-._~+/]{20,}"
    r"|eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+)",
    re.IGNORECASE
)

# Rule 2: credential keyword + flexible separator + value
# Separators: = : - / space, or no separator at all (e.g. "keyAbc123")
# Value: 6+ non-whitespace chars — must also pass _value_looks_like_secret()
_KEYWORD_VALUE_RE = re.compile(
    r"\b(password|passwd|pwd|secret|token|credential"
    r"|api[_\-]?key|access[_\-]?key|private[_\-]?key"
    r"|auth[_\-]?token|auth[_\-]?key|client[_\-]?secret"
    r"|key|pass)"
    r"[\s:=\-/]*"      # flexible separator: any combo of space :=-/ or nothing
    r"([^\s]{6,})",    # value: 6+ non-whitespace chars
    re.IGNORECASE
)

# Rule 3: standalone secret — 15+ chars, mixed letters+digits, no spaces
# Handles both orderings: letters-then-digits and digits-then-letters
_STANDALONE_SECRET_RE = re.compile(
    r"(?<![a-zA-Z])"
    r"(?=[a-zA-Z0-9]*[a-zA-Z][a-zA-Z0-9]*[0-9]|[a-zA-Z0-9]*[0-9][a-zA-Z0-9]*[a-zA-Z])"
    r"[a-zA-Z0-9\-._]{12,}"
    r"(?![a-zA-Z0-9])"
)


def _value_looks_like_secret(value: str) -> bool:
    """Value must contain both at least one digit and one letter to be a secret."""
    return any(c.isdigit() for c in value) and any(c.isalpha() for c in value)


def is_sensitive(text: str) -> bool:
    if not text:
        return False

    # Rule 1: explicit known formats
    if _EXPLICIT_TOKEN_RE.search(text):
        return True

    # Rule 2: keyword + separator + mixed-char value
    m = _KEYWORD_VALUE_RE.search(text)
    if m and _value_looks_like_secret(m.group(2)):
        return True

    # Rule 3: raw secret dump — only when text doesn't look like a normal sentence
    # (3+ normal alphabetic words = sentence, skip rule 3 to avoid false positives)
    words = text.split()
    normal_word_count = sum(1 for w in words if w.isalpha() and len(w) >= 3)
    if normal_word_count < 3 and _STANDALONE_SECRET_RE.search(text):
        return True

    return False