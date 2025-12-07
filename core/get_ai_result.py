from openai import OpenAI
from common.config import Config

config = Config()
llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)

def get_ai_result(prompt, request):
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": request + "\n---\n" + prompt
        }
    ]

    try:
        completion = llm_client.chat.completions.create(
            model=config.llm_model,
            messages=messages,
            timeout=config.llm_timeout
        )

        response_content = completion.choices[0].message.content
        return response_content
    except Exception as e:
        from common.logger import logger
        logger.error(f"Error in get_ai_result: {e}")
