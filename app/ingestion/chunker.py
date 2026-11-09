from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from app.utils.helpers import estimate_tokens


@dataclass
class Chunk:
    """Represents a text chunk with positional metadata."""
    chunk_index: int
    content: str
    token_count: int
    metadata: Dict[str, Any]


class TextChunker:
    """Recursive character chunker with overlap and metadata propagation."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text by separators until sub-chunks are within size limits."""
        if not separators or len(text) <= self.chunk_size:
            return [text] if text else []

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep == "":
            # Character by character fallback
            return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        parts = text.split(sep)
        splits = []
        for part in parts:
            if not part:
                continue
            if len(part) <= self.chunk_size:
                splits.append(part)
            else:
                splits.extend(self._split_text(part, remaining_seps))
        return splits

    def chunk(self, text: str, base_metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Chunk input text and return list of Chunk instances."""
        if not text.strip():
            return []

        base_meta = base_metadata or {}
        raw_splits = self._split_text(text, self.separators)

        chunks: List[Chunk] = []
        current_chunk_parts: List[str] = []
        current_length = 0

        for part in raw_splits:
            part_len = len(part)
            if current_length + part_len + 1 > self.chunk_size and current_chunk_parts:
                chunk_str = " ".join(current_chunk_parts).strip()
                if chunk_str:
                    meta = dict(base_meta)
                    meta["chunk_index"] = len(chunks)
                    chunks.append(
                        Chunk(
                            chunk_index=len(chunks),
                            content=chunk_str,
                            token_count=estimate_tokens(chunk_str),
                            metadata=meta,
                        )
                    )

                # Keep overlap for next chunk
                overlap_parts = []
                overlap_len = 0
                for p in reversed(current_chunk_parts):
                    if overlap_len + len(p) <= self.chunk_overlap:
                        overlap_parts.insert(0, p)
                        overlap_len += len(p)
                    else:
                        break
                current_chunk_parts = overlap_parts
                current_length = overlap_len

            current_chunk_parts.append(part)
            current_length += part_len + 1

        if current_chunk_parts:
            final_str = " ".join(current_chunk_parts).strip()
            if final_str:
                meta = dict(base_meta)
                meta["chunk_index"] = len(chunks)
                chunks.append(
                    Chunk(
                        chunk_index=len(chunks),
                        content=final_str,
                        token_count=estimate_tokens(final_str),
                        metadata=meta,
                    )
                )

        return chunks
