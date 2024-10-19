from flask import request, abort, jsonify
import hmac
import hashlib
import concurrent.futures
from common.logger import logger
import traceback

import miniflux
from common.config import Config
from core import process_entry
from myapp import app

config = Config()
miniflux_client = miniflux.Client(config.miniflux_base_url, api_key=config.miniflux_api_key)

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
        logger.info('Get unread entries via webhook: ' + str(len(entries['entries'])))
        for i in entries['entries']:
            i['feed'] = entries['feed']
            with concurrent.futures.ThreadPoolExecutor(max_workers=config.llm_max_workers) as executor:
                futures = [executor.submit(process_entry, miniflux_client, i)]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        data = future.result()
                        return jsonify(data), 200
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        logger.error('generated an exception: %s' % e)
                        return 500
