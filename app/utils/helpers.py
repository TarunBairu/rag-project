import hashlib
import re
from pathlib import Path
from typing import Union


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def normalize_text(text: str) -> str:
    """Clean and normalize whitespace, newlines, and special characters."""
    if not text:
        return ""
    # Replace carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple consecutive newlines (more than 2) into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse irregular horizontal spaces
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    """Estimate token count using 4 characters per token heuristic."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def format_bytes(size: Union[int, float]) -> str:
    """Convert bytes to human readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and remove unsafe chars."""
    clean = Path(filename).name
    # Keep alphanumeric, dot, hyphen, underscore
    clean = re.sub(r"[^\w\s\.-]", "_", clean)
    return clean.strip() or "unnamed_document"


def get_file_extension(filename: str) -> str:
    """Return lowercase file extension without the dot."""
    ext = Path(filename).suffix.lower()
    return ext.lstrip(".")
