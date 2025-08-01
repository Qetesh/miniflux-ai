import time
import miniflux
import traceback
from common import config, logger


def _init_miniflux_client():
    """
    Create and test Miniflux client connection
    
    Returns:
        miniflux.Client: Authenticated and tested Miniflux client
    """
    client = miniflux.Client(config.miniflux_base_url, api_key=config.miniflux_api_key)
    
    # Test connection with retry logic
    while True:
        try:
            alive = client.me()
            logger.info('Successfully connected to Miniflux!')
            break
        except Exception as e:
            logger.error(f'Cannot connect to Miniflux: {e}')
            logger.error(traceback.format_exc())
            time.sleep(3)
    
    return client


miniflux_client = _init_miniflux_client()