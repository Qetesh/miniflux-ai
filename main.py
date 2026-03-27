import concurrent.futures
import time
import traceback

import miniflux
import schedule

from common import Config, logger
from services.feeds_status_service import ensure_miniflux_feed, generate_feeds_status, resolve_feeds_status_url
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


def resolve_ai_news_url():
    if not config.ai_news_url:
        return None
    return config.ai_news_url.rstrip('/') + '/rss/ai-news'

def my_schedule():
    if config.miniflux_schedule_interval:
        interval = config.miniflux_schedule_interval
    else:
        interval = 15 if config.miniflux_webhook_secret else 1
    schedule.every(interval).minutes.do(fetch_unread_entries, config, miniflux_client)
    schedule.run_all()

    if config.ai_news_schedule:
        ensure_miniflux_feed(miniflux_client, resolve_ai_news_url(), 'ai_news')
        for ai_schedule in config.ai_news_schedule:
            schedule.every().day.at(ai_schedule).do(generate_daily_news, miniflux_client)
            logger.info(f"Successfully added the ai_news schedule: {ai_schedule}")

    if config.feeds_status_enabled:
        ensure_miniflux_feed(miniflux_client, resolve_feeds_status_url(config.feeds_status_url), 'feeds_status')
        schedule.every().day.at(config.feeds_status_schedule).do(
            generate_feeds_status,
            miniflux_client,
            config.feeds_status_url,
        )
        logger.info(f"Successfully added the feeds_status schedule: {config.feeds_status_schedule}")

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
        if config.ai_news_schedule or config.miniflux_webhook_secret or config.feeds_status_enabled:
            executor.submit(my_flask)
        executor.submit(my_schedule)
