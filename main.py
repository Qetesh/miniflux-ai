import concurrent.futures
import time

import miniflux
from markdownify import markdownify as md
import markdown
from openai import OpenAI
from yaml import load, Loader

config = load(open('config.yml', encoding='utf8'), Loader=Loader)
miniflux_client = miniflux.Client(config['miniflux']['base_url'], api_key=config['miniflux']['api_key'])
llm_client = OpenAI(base_url=config['llm']['base_url'], api_key=config['llm']['api_key'])

def process_entry(entry):
    llm_result = ''
    start_with_list = [name[1]['title'] for name in config['agents'].items()]
    style_block = [name[1]['style_block'] for name in config['agents'].items()]
    [start_with_list.append('<pre') for i in style_block if i]

    for agent in config['agents'].items():
        messages = [
            {"role": "system", "content": agent[1]['prompt']},
            {"role": "user", "content": "The following is the input content:\n---\n " + md(entry['content']) }
        ]
        # filter, if AI is not generating, and in whitelist, or not in blacklist
        if ((not entry['content'].startswith(tuple(start_with_list))) and
                (((agent[1]['whitelist'] is not None) and (entry['feed']['site_url'] in agent[1]['whitelist'])) or
                 (agent[1]['blacklist'] is not None and entry['feed']['site_url'] not in agent[1]['blacklist']) or
                 (agent[1]['whitelist'] is None and agent[1]['blacklist'] is None))):
            completion = llm_client.chat.completions.create( model=config['llm']['model'], messages= messages, timeout=15 )
            response_content = completion.choices[0].message.content
            print(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()), agent[0], entry['feed']['feed_url'], response_content)

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
    print(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()), 'Fetched unread entries: ' + str(len(entries['entries']))) if len(entries['entries']) > 0 else print(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()), 'No new entries')

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_entry, i) for i in entries['entries']]
        for future in concurrent.futures.as_completed(futures):
            try:
                data = future.result()
            except Exception as e:
                print('generated an exception: %s' % e)

    if len(entries['entries']) > 0 and time.time() - start_time >= 3:
        print(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()), 'Done')
    time.sleep(60)