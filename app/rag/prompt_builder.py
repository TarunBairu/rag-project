from typing import Any, Dict, List
from app.utils.helpers import estimate_tokens


class PromptBuilder:
    """Builds grounded prompts with context citations and instructions."""

    SYSTEM_PROMPT = (
        "You are an expert AI assistant powering a Retrieval-Augmented Generation (RAG) system. "
        "Answer the user's question accurately and concisely using ONLY the provided context snippets. "
        "Rules:\n"
        "1. Strictly ground your answer in the provided context.\n"
        "2. If the context does not contain enough information to answer the question, state: "
        "'Based on the provided documents, I do not have enough information to answer this question.'\n"
        "3. Explicitly cite your sources using bracketed citations, e.g., [Source 1], [Source 2].\n"
        "4. Do not make up facts or assumptions not present in the excerpts."
    )

    @classmethod
    def format_context(cls, retrieved_chunks: List[Dict[str, Any]], max_tokens: int = 2500) -> str:
        """Format retrieved chunks into numbered citations within token budget."""
        if not retrieved_chunks:
            return "No relevant context found."

        formatted_snippets = []
        accumulated_tokens = 0

        for i, chunk in enumerate(retrieved_chunks, start=1):
            text = chunk.get("document") or chunk.get("content") or ""
            meta = chunk.get("metadata") or {}
            filename = meta.get("filename", "Unknown Document")
            chunk_idx = meta.get("chunk_index", "0")
            score = chunk.get("score", 0.0)

            snippet = (
                f"[Source {i} | Doc: {filename} | Chunk: {chunk_idx} | Similarity: {score:.3f}]\n"
                f"{text}\n"
            )

            tok_count = estimate_tokens(snippet)
            if accumulated_tokens + tok_count > max_tokens and formatted_snippets:
                break

            formatted_snippets.append(snippet)
            accumulated_tokens += tok_count

        return "\n".join(formatted_snippets)

    @classmethod
    def build_prompt(cls, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, str]:
        """Construct system prompt and user prompt payload."""
        context_str = cls.format_context(retrieved_chunks)
        user_message = (
            f"Context Information:\n"
            f"---------------------\n"
            f"{context_str}\n"
            f"---------------------\n\n"
            f"User Question: {query}\n\n"
            f"Provide a well-grounded response with explicit source citations:"
        )

        return {
            "system_prompt": cls.SYSTEM_PROMPT,
            "user_prompt": user_message,
        }
