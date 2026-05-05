import unittest
from unittest.mock import patch

from core import token_truncation


class CharacterEncoding:
    def encode(self, text):
        return list(text)

    def decode(self, tokens):
        return "".join(tokens)


class TokenTruncationTestCase(unittest.TestCase):
    def test_zero_or_negative_limit_returns_original_content(self):
        result = token_truncation.truncate_text_to_tokens(
            "abcdef",
            0,
            model="unknown-model",
        )

        self.assertEqual(result, "abcdef")

    def test_truncates_tail_and_keeps_leading_tokens(self):
        with patch.object(
            token_truncation,
            "get_token_encoding",
            return_value=CharacterEncoding(),
        ):
            result = token_truncation.truncate_text_to_tokens(
                "abcdef",
                3,
                model="test-model",
            )

        print("test_truncates_tail_and_keeps_leading_tokens result:", result)
        self.assertEqual(result, "abc")

    def test_short_content_is_not_truncated(self):
        with patch.object(
            token_truncation,
            "get_token_encoding",
            return_value=CharacterEncoding(),
        ):
            result = token_truncation.truncate_text_to_tokens(
                "abc",
                5,
                model="test-model",
            )

        print("test_short_content_is_not_truncated result:", result)
        self.assertEqual(result, "abc")

    def test_unknown_model_falls_back_to_base_encoding(self):
        class FakeTiktoken:
            @staticmethod
            def encoding_for_model(model):
                raise KeyError(model)

            @staticmethod
            def get_encoding(name):
                if name == "o200k_base":
                    return "fallback-encoding"
                raise AssertionError(f"unexpected encoding {name}")

        with patch.object(token_truncation, "tiktoken", FakeTiktoken):
            encoding = token_truncation.get_token_encoding("qwen3.5-9B")

        self.assertEqual(encoding, "fallback-encoding")


if __name__ == "__main__":
    unittest.main()
