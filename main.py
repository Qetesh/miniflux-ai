import concurrent.futures
import time

import miniflux
import schedule
from common import Config, logger

config = Config()
from myapp import app
from core import fetch_unread_entries

miniflux_client = miniflux.Client(config.miniflux_base_url, api_key=config.miniflux_api_key)

def my_schedule():
    interval = 15 if config.miniflux_webhook_secret else 1
    schedule.every(interval).minutes.do(fetch_unread_entries, config, miniflux_client)
    schedule.run_all()

    while True:
        schedule.run_pending()
        time.sleep(1)

def my_flask():
    logger.info('Starting API')
    app.run(host='0.0.0.0', port=8000)

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(my_flask)
        executor.submit(my_schedule)
