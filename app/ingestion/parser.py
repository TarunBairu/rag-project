import re
from typing import Any, Dict
from app.utils.helpers import normalize_text, estimate_tokens


class DocumentParser:
    """Parses raw text and extracts structural metadata."""

    @staticmethod
    def parse(text: str, filename: str = "") -> Dict[str, Any]:
        """Normalize text and extract metadata."""
        cleaned_text = normalize_text(text)
        lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]
        
        # Heuristic title detection from first non-empty line
        title = filename
        if lines:
            first_line = lines[0]
            if len(first_line) <= 120 and not first_line.endswith((".", "!", "?")):
                title = re.sub(r"^#+\s*", "", first_line)

        metadata = {
            "title": title,
            "filename": filename,
            "character_count": len(cleaned_text),
            "word_count": len(cleaned_text.split()),
            "estimated_tokens": estimate_tokens(cleaned_text),
            "line_count": len(lines),
        }

        return {
            "cleaned_text": cleaned_text,
            "metadata": metadata,
        }
