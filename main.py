import concurrent.futures
import time
import traceback
from common.logger import logger
from core.entry_filter import filter_entry

import miniflux
from markdownify import markdownify as md
import markdown
from openai import OpenAI
from yaml import safe_load

config = safe_load(open('config.yml', encoding='utf8'))
miniflux_client = miniflux.Client(config['miniflux']['base_url'], api_key=config['miniflux']['api_key'])
llm_client = OpenAI(base_url=config['llm']['base_url'], api_key=config['llm']['api_key'])

def process_entry(entry):
    llm_result = ''

    for agent in config['agents'].items():
        messages = [
            {"role": "system", "content": agent[1]['prompt']},
            {"role": "user", "content": "The following is the input content:\n---\n " + md(entry['content']) }
        ]
        # filter, if AI is not generating, and in allow_list, or not in deny_list
        if filter_entry(config, agent, entry):
            completion = llm_client.chat.completions.create(
                model=config['llm']['model'],
                messages= messages,
                timeout=config.get('llm', {}).get('timeout', 60)
            )

            response_content = completion.choices[0].message.content
            logger.info(f"agents:{agent[0]} feed_title:{entry['title']} result:{response_content}")

            if agent[1]['style_block']:
                llm_result = (llm_result + '<pre style="white-space: pre-wrap;"><code>\n'
                              + agent[1]['title'] + '：'
                              + response_content.replace('\n', '').replace('\r', '')
                              + '\n</code></pre><hr><br />')
            else:
                llm_result = llm_result + f"{agent[1]['title']}：{markdown.markdown(response_content)}<hr><br />"

    if len(llm_result) > 0:
        miniflux_client.update_entry(entry['id'], content= llm_result + entry['content'])

while True:
    entries = miniflux_client.get_entries(status=['unread'], limit=10000)
    start_time = time.time()
    logger.info('Fetched unread entries: ' + str(len(entries['entries']))) if len(entries['entries']) > 0 else logger.info('No new entries')

    with concurrent.futures.ThreadPoolExecutor(max_workers=config.get('llm', {}).get('max_workers', 4)) as executor:
        futures = [executor.submit(process_entry, i) for i in entries['entries']]
        for future in concurrent.futures.as_completed(futures):
            try:
                data = future.result()
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error('generated an exception: %s' % e)

    if len(entries['entries']) > 0 and time.time() - start_time >= 3:
        logger.info('Done')
    time.sleep(60)