import concurrent.futures
import time
import traceback

import miniflux
import schedule

from common import Config, logger
from myapp import app
from core import fetch_unread_entries, generate_daily_news

config = Config()
miniflux_client = miniflux.Client(config.miniflux_base_url, api_key=config.miniflux_api_key)
while True:
    try:
        alive = miniflux_client.me()
        logger.info('Successfully connected to Miniflux!')
        break
    except Exception as e:
        logger.error('Cannot connect to Miniflux: %s' % e)
        # logger.error(e.args[0].content)
        time.sleep(3)

def my_schedule():
    if config.miniflux_schedule_interval:
        interval = config.miniflux_schedule_interval
    else:
        interval = 15 if config.miniflux_webhook_secret else 1
    schedule.every(interval).minutes.do(fetch_unread_entries, config, miniflux_client)
    schedule.run_all()

    if config.ai_news_schedule:
        feeds = miniflux_client.get_feeds()
        if not any('Newsᴬᴵ for you' in item['title'] for item in feeds):
            try:
                miniflux_client.create_feed(category_id=1, feed_url=config.ai_news_url + '/rss/ai-news')
                logger.info('Successfully created the ai_news feed in Miniflux!')
            except Exception as e:
                logger.error('Failed to create the ai_news feed in Miniflux: %s' % e)
        for ai_schedule in config.ai_news_schedule:
            schedule.every().day.at(ai_schedule).do(generate_daily_news, miniflux_client)
            logger.info(f"Successfully added the ai_news schedule: {ai_schedule}")

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"An error occurred in the schedule loop: {e}")
            logger.error(traceback.format_exc())
            time.sleep(30)

def my_flask():
    logger.info('Starting API')
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(my_flask)
        executor.submit(my_schedule)
