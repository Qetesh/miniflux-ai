from markdownify import markdownify as md

import litellm
from litellm.exceptions import (
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    RateLimitError,
    Timeout,
)
from openai import OpenAI
from google import genai
from google.genai import types
from common.config import Config
from common.logger import logger

config = Config()

if not config.llm_provider or config.llm_provider == "openai":
    llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)
elif config.llm_provider == "gemini":
    llm_client = genai.Client(
        http_options=types.HttpOptions(base_url=config.llm_base_url),
        api_key=config.llm_api_key,
    )
elif config.llm_provider == "litellm":
    llm_client = None


def _build_messages(prompt: str, request: str):
    if "${content}" in prompt:
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt.replace("${content}", md(request))},
        ]
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "The following is the input content:\n---\n " + md(request)},
    ]


def get_ai_result(prompt: str, request: str):
    if config.llm_max_length and len(request) > config.llm_max_length:
        request = request[: config.llm_max_length]

    if config.llm_provider == "gemini":
        try:
            if "${content}" in prompt:
                instruction = ["You are a helpful assistant."]
                contents = prompt.replace("${content}", md(request))
            else:
                instruction = [prompt]
                contents = "The following is the input content:\n---\n " + md(request)

            response = llm_client.models.generate_content(
                model=config.llm_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=instruction,
                    **config.llm_extra_params,
                ),
            )
            return response.text
        except Exception as e:
            logger.error(f"Error in get_ai_result (Gemini): {e}")
            raise
    elif config.llm_provider == "litellm":
        messages = _build_messages(prompt, request)
        kwargs = {
            "model": config.llm_model,
            "messages": messages,
            "timeout": config.llm_timeout,
            "drop_params": True,
            **config.llm_extra_params,
        }
        if config.llm_api_key:
            kwargs["api_key"] = config.llm_api_key
        if config.llm_base_url:
            kwargs["api_base"] = config.llm_base_url

        try:
            completion = litellm.completion(**kwargs)
            content = completion.choices[0].message.content
            if content is None:
                logger.warning("LiteLLM returned empty response content")
                return ""
            return content
        except AuthenticationError as e:
            logger.error(f"LiteLLM authentication failed (check API key): {e}")
            raise
        except NotFoundError as e:
            logger.error(f"LiteLLM model not found (check model string format, e.g. 'openai/gpt-4o'): {e}")
            raise
        except RateLimitError as e:
            logger.error(f"LiteLLM rate limit exceeded: {e}")
            raise
        except Timeout as e:
            logger.error(f"LiteLLM request timed out: {e}")
            raise
        except BadRequestError as e:
            logger.error(f"LiteLLM bad request (check model/params): {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_ai_result (LiteLLM): {e}")
            raise
    else:
        messages = _build_messages(prompt, request)

        try:
            completion = llm_client.chat.completions.create(
                model=config.llm_model,
                messages=messages,
                timeout=config.llm_timeout,
                **config.llm_extra_params,
            )

            response_content = completion.choices[0].message.content
            return response_content
        except Exception as e:
            logger.error(f"Error in get_ai_result (OpenAI): {e}")
            raise
