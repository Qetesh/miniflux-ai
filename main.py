import os
import time

from openai import OpenAI
import miniflux
from markdownify import markdownify as md
import concurrent.futures

miniflux_base_url = os.getenv('miniflux_base_url')
miniflux_api_key = os.getenv('miniflux_api_key')
llm_base_url = os.getenv('llm_base_url')
llm_api_key = os.getenv('llm_api_key')
llm_model = os.getenv('llm_model')

miniflux_client = miniflux.Client(miniflux_base_url, api_key=miniflux_api_key)
llm_client = OpenAI(base_url=llm_base_url, api_key=llm_api_key)

def process_entry(entry):
    if not entry['content'].startswith('摘要'):
        completion = llm_client.chat.completions.create(
            model=llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a highly skilled AI assistant capable of understanding and summarizing complex content from various "
                        "Your task is to read the provided content, understand the main points, and produce a concise summary in Chinese."
                        "Limit the summary to 50 words and 2 sentences. Do not add any additional text."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "Summarize the following content in Chinese: 'The latest advancements in AI chip technology have enabled "
                        "faster processing speeds and lower energy consumption. These innovations are paving the way for more efficient "
                        "machine learning models, and companies are rapidly adopting these technologies to stay competitive.'"
                    )
                },
                {
                    "role": "assistant",
                    "content": (
                        "最新的AI芯片技术取得了突破，使处理速度更快、能耗更低。这些创新为更高效的机器学习模型铺平了道路，企业纷纷采用这些技术以保持竞争力。"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "Summarize the following content in Chinese: 'The government has announced new policies aimed at reducing "
                        "carbon emissions by 2030. These measures include investing in renewable energy, imposing stricter regulations "
                        "on industries, and promoting electric vehicles. Experts believe these policies will significantly reduce the "
                        "country's carbon footprint.'"
                    )
                },
                {
                    "role": "assistant",
                    "content": (
                        "政府宣布了到2030年减少碳排放的新政策，包括投资可再生能源、加强行业监管和推广电动汽车。专家认为这些政策将显著减少国家的碳足迹。"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "Summarize the following content in Chinese: 'Participants are debating the pros and cons of remote work. "
                        "Some argue that it increases productivity and work-life balance, while others believe it leads to isolation and "
                        "decreased collaboration. Overall, the consensus is that remote work is beneficial if managed properly.'"
                    )
                },
                {
                    "role": "assistant",
                    "content": (
                        "论坛讨论了远程工作的利弊。有人认为它提高了生产力和平衡了工作与生活，有人则认为它导致孤立和减少了协作。总体而言，大家认为远程工作在管理得当的情况下是有益的。"
                    )
                },
                {
                    "role": "user",
                    "content": (
                            "Summarize the following content in Chinese: '" + md(entry['content']) + "'"
                    )
                }
            ]
        )
        llm_result = completion.choices[0].message.content
        print(llm_result)
        miniflux_client.update_entry(entry['id'], content='摘要：' + llm_result + '<hr><br />' + entry['content'])
    return None

while True:
    # Fetch entries with status unread
    entries = miniflux_client.get_entries(status=['unread'], limit=10000)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_entry, i) for i in entries['entries']]
    time.sleep(60)