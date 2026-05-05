from typing import Optional

import tiktoken


def get_token_encoding(model: Optional[str] = None):
    if model:
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            pass

    for encoding_name in ("o200k_base", "cl100k_base"):
        try:
            return tiktoken.get_encoding(encoding_name)
        except ValueError:
            continue

    raise ValueError("No supported tiktoken encoding is available")


def count_text_tokens(text: str, model: Optional[str] = None) -> int:
    return len(get_token_encoding(model).encode(text or ""))


def truncate_text_to_tokens(text: str, max_tokens: int, model: Optional[str] = None) -> str:
    if max_tokens <= 0:
        return text

    encoding = get_token_encoding(model)
    tokens = encoding.encode(text or "")
    if len(tokens) <= max_tokens:
        return text
    return encoding.decode(tokens[:max_tokens])
