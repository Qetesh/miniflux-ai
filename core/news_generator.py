import json
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.logger import logger
from common import config, SUMMARY_FILE_LOCK, SUMMARY_FILE, AI_NEWS_FILE
from core.llm_client import get_completion

FEED_NAME = 'Newsᴬᴵ for you'


def init_news_feed(miniflux_client) -> None:
    """
    Initialize AI news feed if it doesn't exist in Miniflux
    
    Args:
        miniflux_client: Miniflux client instance
    """
    try:
        logger.debug('Checking if AI news feed exists')
        
        feeds = miniflux_client.get_feeds()
        ai_news_feed_id = _find_news_feed_id(feeds)
        
        if ai_news_feed_id is None:
            _create_news_feed(miniflux_client)
        else:
            logger.debug(f'AI news feed already exists with ID: {ai_news_feed_id}')
            
    except Exception as e:
        logger.error(f'Failed to initialize AI news feed: {e}')
        raise


def _create_news_feed(miniflux_client) -> None:
    """
    Create AI news feed in Miniflux
    
    Args:
        miniflux_client: Miniflux client instance
    """
    try:
        feed_url = f"{config.ai_news_url}/rss/ai-news"
        logger.debug(f'Creating AI news feed with URL: {feed_url}')
        
        miniflux_client.create_feed(category_id=1, feed_url=feed_url)
        logger.info(f'Successfully created AI news feed in Miniflux: {feed_url}')
        
    except Exception as e:
        logger.error(f'Failed to create AI news feed in Miniflux: {e}')
        raise


def generate_daily_news(miniflux_client) -> None:
    """
    Generate daily news from AI summaries and refresh corresponding feed
    
    Args:
        miniflux_client: Miniflux client instance for feed refresh
    """
    logger.info('Starting daily news generation')
    
    try:
        summaries = _load_summaries()
        if not summaries:
            logger.info('No summaries found, skipping news generation')
            return
            
        logger.info(f'Loaded {len(summaries)} summaries for processing')
        
        news_content = _generate_news_content(summaries)
        _save_news_content(news_content)
        _refresh_ai_news_feed(miniflux_client)
        
        logger.info('Daily news generation completed successfully')
        
    except Exception as e:
        logger.error(f'Failed to generate daily news: {e}')
        logger.error(traceback.format_exc())


def _load_summaries() -> List[Dict[str, Any]]:
    """
    Load summaries from file
    
    Returns:
        List of summary dictionaries, empty list if file not found or invalid
    """
    with SUMMARY_FILE_LOCK:
        try:
            logger.debug(f'Loading and clearing summaries from {SUMMARY_FILE}')
            
            if not SUMMARY_FILE.exists():
                logger.debug('Summary file does not exist')
                return []
                
            # Read and parse summaries
            with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                summaries = [json.loads(line) for line in lines if line.strip()]

            return summaries
            
        except Exception as e:
            logger.error(f'Unexpected error loading summaries: {e}')
            logger.error(traceback.format_exc())
            return []
        
        finally:
            SUMMARY_FILE.write_text('', encoding='utf-8')


def _generate_news_content(summaries: List[Dict[str, Any]]) -> str:
    """
    Generate news content using LLM based on summaries
    
    Args:
        summaries: List of summary dictionaries
        
    Returns:
        Generated news content string
    """
    try:
        contents = '\n'.join([summary['content'] for summary in summaries])
        
        # Generate greeting with current timestamp
        current_time = time.strftime('%B %d, %Y at %I:%M %p')
        logger.debug(f'Generating greeting for time: {current_time}')
        greeting = get_completion(config.ai_news_prompts['greeting'], current_time)
        
        # Generate summary block from all contents
        logger.debug('Generating summary block from combined contents')
        summary_block = get_completion(config.ai_news_prompts['summary_block'], contents)
        
        # Generate executive summary from summary block
        logger.debug('Generating executive summary')
        summary = get_completion(config.ai_news_prompts['summary'], summary_block)
        
        # Combine all parts into final content
        response_content = f"{greeting}\n\n### 🌐Summary\n{summary}\n\n### 📝News\n{summary_block}"
        
        return response_content
        
    except Exception as e:
        logger.error(f'Failed to generate news content: {e}')
        raise


def _save_news_content(content: str) -> None:
    """
    Save generated news content to file
    
    Args:
        content: Generated news content to save
    """
    try:
        AI_NEWS_FILE.write_text(content, encoding='utf-8')
        
    except Exception as e:
        logger.error(f'Failed to save news content: {e}')
        raise


def _refresh_ai_news_feed(miniflux_client) -> None:
    """
    Find and refresh the AI news feed in Miniflux
    
    Args:
        miniflux_client: Miniflux client instance
    """
    try:
        feeds = miniflux_client.get_feeds()
        ai_news_feed_id = _find_news_feed_id(feeds)
        
        if ai_news_feed_id:
            logger.debug(f'Found AI news feed with ID: {ai_news_feed_id}')
            miniflux_client.refresh_feed(ai_news_feed_id)
            logger.info('Successfully refreshed AI news feed in Miniflux')
        else:
            # Feed should have been initialized at startup; avoid recreating to prevent potential issues
            logger.warning('AI news feed not found in Miniflux')
            
    except Exception as e:
        logger.error(f'Failed to refresh AI news feed: {e}')
        raise


def _find_news_feed_id(feeds: List[Dict[str, Any]]) -> Optional[int]:
    """
    Find the AI news feed ID from the list of feeds
    
    Args:
        feeds: List of feed dictionaries from Miniflux
        
    Returns:
        Feed ID if found, None otherwise
    """
    for feed in feeds:
        if FEED_NAME in feed.get('title', ''):
            return feed['id']
    return None
        