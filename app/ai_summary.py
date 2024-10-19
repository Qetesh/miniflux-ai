from flask import request, abort
import hmac
import hashlib
import concurrent.futures
from common.logger import logger
import traceback

from common.config import Config
from core import process_entry
from app import app

config = Config()
@app.route('/api/miniflux-ai', methods=['POST'])
def miniflux_ai():
    """miniflux Webhook API
    publish new feed entries to this API endpoint
    ---
    post:
      description: Create a random pet
      parameters:
        - in: body
          name: body
          required: True
      responses:
        200:
          content:
            application/json:
              status: string
    """
    webhook_secret = config.miniflux_webhook_secret

    if request.method == 'POST':
        payload = request.get_data()
        signature = request.headers.get('X-Miniflux-Signature')
        hmac_signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(hmac_signature, signature):
            abort(403)  # 返回403 Forbidden
        entries = request.json
        logger.info('Fetched unread entries: ' + str(len(entries['entries'])))
        for i in entries['entries']:
            i['feed'] = entries['feed']
            with concurrent.futures.ThreadPoolExecutor(max_workers=config.get('llm', {}).get('max_workers', 4)) as executor:
                futures = [executor.submit(process_entry, miniflux_client, i)]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        data = future.result()
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        logger.error('generated an exception: %s' % e)
