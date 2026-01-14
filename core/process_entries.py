import json
import markdown
from ratelimit import limits, sleep_and_retry
import threading

from common.config import Config
from common.logger import logger
from core.entry_filter import filter_entry
from core.get_ai_result import get_ai_result

config = Config()
file_lock = threading.Lock()

@sleep_and_retry
@limits(calls=config.llm_RPM, period=60)
def process_entry(miniflux_client, entry):
    #Todo change to queue
    llm_result = ''

    for agent in config.agents.items():
        # filter, if AI is not generating, and in allow_list, or not in deny_list
        if filter_entry(config, agent, entry):

            try:
                response_content = get_ai_result(agent[1]["prompt"], entry["content"])
            except Exception as e:
                logger.error(
                    f"Error processing entry {entry['id']} with agent {agent[0]}: {e}"
                )
                continue
            log_content = (response_content or "")[:20] + '...' if len(response_content or "") > 20 else response_content
            logger.info(f"agents:{agent[0]} feed_id:{entry['id']} result:{log_content}")

            # save for ai_summary
            if agent[0] == 'summary':
                entry_list = {
                    'datetime': entry['created_at'],
                    'category': entry['feed']['category']['title'],
                    'title': entry['title'],
                    'content': response_content,
                    'url': entry['url']
                }
                with file_lock:
                    try:
                        with open('entries.json', 'r') as file:
                            data = json.load(file)
                    except (FileNotFoundError, json.JSONDecodeError):
                        data = []
                    data.append(entry_list)
                    with open('entries.json', 'w') as file:
                        json.dump(data, file, indent=4, ensure_ascii=False)

            if agent[1]['style_block']:
                llm_result = (llm_result + '<blockquote>\n  <p><strong>'
                              + agent[1]['title'] + '</strong> '
                              + response_content.replace('\n', '').replace('\r', '')
                              + '\n</p>\n</blockquote><br/>')
            else:
                llm_result = llm_result + f"{agent[1]['title']}{markdown.markdown(response_content)}<hr><br />"

    if len(llm_result) > 0:
        dict_result = miniflux_client.update_entry(entry['id'], content= llm_result + entry['content'])
