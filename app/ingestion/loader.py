import csv
import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, Union

from app.ingestion.parser import DocumentParser
from app.utils.helpers import get_file_extension, sanitize_filename

logger = logging.getLogger("rag.ingestion.loader")


class DocumentLoader:
    """Loads and extracts text content from various file formats."""

    @staticmethod
    def load_from_bytes(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Load text from in-memory byte buffer based on extension."""
        safe_name = sanitize_filename(filename)
        ext = get_file_extension(safe_name)

        text = ""
        extra_meta: Dict[str, Any] = {}

        if ext in ["txt", "md"]:
            text = file_bytes.decode("utf-8", errors="replace")

        elif ext == "csv":
            decoded = file_bytes.decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(decoded))
            rows = []
            for row in reader:
                rows.append(" | ".join(row))
            text = "\n".join(rows)
            extra_meta["row_count"] = len(rows)

        elif ext == "json":
            decoded = file_bytes.decode("utf-8", errors="replace")
            try:
                data = json.loads(decoded)
                text = json.dumps(data, indent=2)
            except Exception:
                text = decoded

        elif ext == "pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(file_bytes))
                page_texts = []
                for i, page in enumerate(reader.pages):
                    extracted = page.extract_text() or ""
                    page_texts.append(extracted)
                text = "\n\n".join(page_texts)
                extra_meta["pages"] = len(reader.pages)
            except ImportError:
                logger.warning("pypdf not installed. Falling back to raw text parsing for PDF.")
                text = file_bytes.decode("utf-8", errors="ignore")
            except Exception as exc:
                logger.error(f"Error parsing PDF ({exc})")
                text = file_bytes.decode("utf-8", errors="ignore")

        elif ext == "docx":
            try:
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    xml_content = zf.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    paragraphs = []
                    for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                        texts = [node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                        if texts:
                            paragraphs.append("".join(texts))
                    text = "\n\n".join(paragraphs)
                    extra_meta["paragraphs"] = len(paragraphs)
            except Exception as exc:
                logger.error(f"Error extracting DOCX: {exc}")
                text = file_bytes.decode("utf-8", errors="ignore")

        else:
            # Default fallback for unrecognized text-like files
            text = file_bytes.decode("utf-8", errors="replace")

        parsed = DocumentParser.parse(text, filename=safe_name)
        parsed["metadata"].update(extra_meta)
        parsed["metadata"]["file_type"] = ext
        parsed["metadata"]["file_size"] = len(file_bytes)

        return {
            "filename": safe_name,
            "file_type": ext,
            "file_size": len(file_bytes),
            "text": parsed["cleaned_text"],
            "metadata": parsed["metadata"],
        }

    @classmethod
    def load_from_path(cls, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load text from a local filesystem path."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(p, "rb") as f:
            content = f.read()
        return cls.load_from_bytes(content, filename=p.name)


def load_file_content(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Helper wrapper for loading file content."""
    return DocumentLoader.load_from_bytes(file_bytes, filename)
