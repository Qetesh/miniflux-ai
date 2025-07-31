from openai import OpenAI
from ratelimit import limits, sleep_and_retry

from common import config

llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)


@sleep_and_retry
@limits(calls=config.llm_RPM, period=60)
def get_completion(system_prompt, user_prompt):
    """
    Get completion from LLM
    
    Args:
        system_prompt (str): System prompt for the LLM
        user_prompt (str): User prompt for the LLM
        
    Returns:
        str: LLM response content
    """
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    completion = llm_client.chat.completions.create(
        model=config.llm_model,
        messages=messages,
        timeout=config.llm_timeout
    )

    response_content = completion.choices[0].message.content
    return response_content

 