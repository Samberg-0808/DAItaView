"""Approximate token counting without requiring tiktoken at runtime."""

# ~4 chars per token is a reliable conservative estimate for English + code
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def estimate_tokens_for_chunks(chunks: list[str]) -> int:
    return sum(estimate_tokens(c) for c in chunks)
