import concurrent.futures
import time
import traceback
from typing import Optional, List, Dict, Any

from common import config
from common.logger import logger
from core.entry_processor import process_entry


def handle_unread_entries(miniflux_client) -> None:
    """
    Fetch and process unread entries from Miniflux
    
    Args:
        miniflux_client: Miniflux client instance
    """
    try:
        entries_data = _fetch_entries_from_miniflux(miniflux_client)
        if not entries_data:
            return

        process_entries_concurrently(miniflux_client, entries_data)
        
    except Exception as e:
        logger.error(f"Failed to fetch and process unread entries: {e}")
        logger.error(traceback.format_exc())


def _fetch_entries_from_miniflux(miniflux_client) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch unread entries from Miniflux
    
    Args:
        miniflux_client: Miniflux client instance
        
    Returns:
        List of unread entries, or None if no entries found
    """
    try:
        logger.info("Starting to fetch unread entries")

        # ascending order can have better logs for viewing the changes
        kwargs = {
            'status': ['unread'],
            'limit': 10000,
            'order': 'id',
            'direction': 'asc'
        }
        
        # Add after parameter if entry_since is configured
        if config.entry_since > 0:
            kwargs['after'] = config.entry_since
            logger.debug(f"Filtering entries after timestamp: {config.entry_since}")
        
        response = miniflux_client.get_entries(**kwargs)
        entries = response.get('entries', [])
        
        logger.info(f'Found {len(entries)} unread entries')
        
        return entries if entries else None
    except Exception as e:
        logger.error(f"Failed to fetch entries from Miniflux: {e}")
        raise


def process_entries_concurrently(miniflux_client, entries: List[Dict[str, Any]]) -> None:
    """
    Process entries concurrently using thread pool
    
    Args:
        miniflux_client: Miniflux client instance
        entries: List of entries to process
    """
    max_workers = config.llm_max_workers
    logger.debug(f"Starting concurrent processing with {max_workers} workers")

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_entry, miniflux_client, entry) 
            for entry in entries
        ]
        _wait_for_completion(futures)
        
    elapsed_time = time.time() - start_time
    logger.info(f'Processing completed in {elapsed_time:.2f} seconds')


def _wait_for_completion(futures: List[concurrent.futures.Future]) -> None:
    """
    Wait for all tasks to complete and handle exceptions
    
    Args:
        futures: List of Future objects
    """
    completed_count = 0
    processed_count = 0
    failed_count = 0
    total_tasks = len(futures)
    
    for future in concurrent.futures.as_completed(futures):
        try:
            processed_agents = future.result()
            completed_count += 1
            if processed_agents:
                processed_count += 1
        except Exception:
            failed_count += 1
            logger.error(traceback.format_exc())
    
    logger.info(f"Processing summary - Total: {total_tasks}, Completed: {completed_count}, Processed: {processed_count}, Failed: {failed_count}")
