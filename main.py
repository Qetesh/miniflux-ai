import concurrent.futures
import time

import schedule

from common import config, logger
from myapp import app
from core import handle_unread_entries, generate_daily_news, init_news_feed, miniflux_client


def my_schedule():
    interval = 15 if config.miniflux_webhook_secret else 1
    schedule.every(interval).minutes.do(handle_unread_entries, miniflux_client)
    schedule.run_all()

    if config.ai_news_schedule:
        init_news_feed(miniflux_client)
        for ai_schedule in config.ai_news_schedule:
            schedule.every().day.at(ai_schedule).do(generate_daily_news, miniflux_client)

    while True:
        schedule.run_pending()
        time.sleep(1)


def my_flask():
    logger.info('Starting API')
    app.run(host='0.0.0.0', port=80)


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(my_flask)
        executor.submit(my_schedule)
