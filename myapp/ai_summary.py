from flask import request, abort, jsonify
import hmac
import hashlib
from common import logger
import traceback

from common import config
from core import process_entries_concurrently, miniflux_client
from myapp import app


@app.route('/api/miniflux-ai', methods=['POST'])
def miniflux_ai():
    """
    Miniflux Webhook API endpoint for processing feed entries
    
    Receives webhook notifications from Miniflux when new feed entries are available.
    Verifies webhook signature, processes entries through AI agents, and returns status.
    
    Returns:
        JSON response with status 'ok' on success, or error details on failure
    
    Raises:
        403: If webhook signature verification fails
        500: If entry processing fails
    """
    try:
        _verify_webhook_signature()

        event_type = request.headers.get('X-Miniflux-Event-Type')
        logger.debug(f'Webhook event type: {event_type}')
        
        if event_type not in ['new_entries']:
            logger.debug(f'Webhook event type not supported: {event_type}')
            return jsonify({'status': 'ok'})

        # Parse and prepare entries data from webhook request
        entries_data = request.json
        logger.debug(f'Webhook request: {entries_data}')
        entries_list = entries_data['entries']
        feed_info = entries_data['feed']
        
        logger.info(f'Get unread entries via webhook: {len(entries_list)}')
        
        for entry in entries_list:
            entry['feed'] = feed_info
        
        process_entries_concurrently(miniflux_client, entries_list)
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f'Failed to process webhook entries: {e}')
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500
    

def _verify_webhook_signature() -> None:
    """
    Verify webhook signature from Miniflux using HMAC-SHA256
    
    Compares the received signature with computed HMAC signature to ensure
    the webhook request is authentic and comes from Miniflux.
    
    Raises:
        403: If signature verification fails
    """
    webhook_secret = config.miniflux_webhook_secret
    payload = request.get_data()
    signature = request.headers.get('X-Miniflux-Signature')

    if not webhook_secret or not signature:
        abort(403)
    
    hmac_signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(hmac_signature, signature):
        abort(403)
