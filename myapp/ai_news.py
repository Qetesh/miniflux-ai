import time
import traceback
from datetime import datetime

import markdown
from feedgen.feed import FeedGenerator
from flask import Response

from common import logger, AI_NEWS_FILE
from myapp import app

FEED_TITLE = 'Newsᴬᴵ for you'
FEED_LINK = 'https://ai-news.miniflux'


@app.route('/rss/ai-news', methods=['GET'])
def miniflux_ai_news() -> Response:
    """
    AI News RSS Feed endpoint
    
    Generates an RSS feed containing daily AI-generated news summaries.
    Loads news content from temporary data file, generates RSS feed with
    welcome entry and daily news entry, then clears the data file.
    
    Returns:
        Response: RSS XML feed content
        
    Raises:
        500: If feed generation fails
    """
    try:
        logger.info('Generating AI news RSS feed')
        
        feed_generator = _create_base_feed()
        _add_welcome_entry(feed_generator)
        
        ai_news_content = _load_news_content()
        if ai_news_content:
            _add_news_entry(feed_generator, ai_news_content)
            logger.debug(f'Successfully loaded news content: {len(ai_news_content)} characters')
        else:
            logger.warning('No news content available, RSS feed contains only welcome entry')
            
        rss_content = feed_generator.rss_str(pretty=True)

        return rss_content
        
    except Exception as e:
        logger.error(f'Failed to generate AI news RSS feed: {e}')
        logger.error(traceback.format_exc())
        raise


def _load_news_content() -> str:
    """
    Load AI news content from data file and clear it
    
    Returns:
        str: News content if available, empty string if file not found or empty
        
    Raises:
        Exception: If file operations fail
    """
    try:
        logger.debug(f'Loading news content from {AI_NEWS_FILE}')
        
        if not AI_NEWS_FILE.exists():
            logger.warning('News content file does not exist')
            return ''

        content = AI_NEWS_FILE.read_text('utf-8')

        return content if content else ''
        
    except Exception as e:
        logger.error(f'Failed to load news content: {e}')
        raise
    finally:
        AI_NEWS_FILE.write_text('', encoding='utf-8')


def _create_base_feed() -> FeedGenerator:
    """
    Create and configure the base RSS feed generator
    
    Returns:
        FeedGenerator: Configured feed generator with base settings
    """
    feed_generator = FeedGenerator()
    feed_generator.id(FEED_LINK)
    feed_generator.title(FEED_TITLE)
    feed_generator.subtitle('Powered by miniflux-ai')
    feed_generator.author({'name': 'miniflux-ai'})
    feed_generator.link(href=FEED_LINK, rel='self')
    return feed_generator


def _add_welcome_entry(feed_generator: FeedGenerator) -> None:
    """
    Add welcome entry to the RSS feed
    
    Args:
        feed_generator: Feed generator to add entry to
    """
    welcome_entry = feed_generator.add_entry()
    welcome_entry.id(FEED_LINK)
    welcome_entry.link(href=FEED_LINK)
    welcome_entry.title('Welcome to Newsᴬᴵ')
    welcome_entry.description('Welcome to Newsᴬᴵ')


def _add_news_entry(feed_generator: FeedGenerator, news_content: str) -> None:
    """
    Add daily news entry to the RSS feed
    
    Args:
        feed_generator: Feed generator to add entry to
        news_content: News content in markdown format
    """
    logger.debug('Adding daily news entry to RSS feed')
    
    timestamp = time.strftime('%Y-%m-%d-%H-%M')
    date_str = time.strftime('%Y-%m-%d')
    time_period = 'Morning' if datetime.today().hour < 12 else 'Nightly'
    
    news_entry = feed_generator.add_entry()
    news_entry.id(f'{FEED_LINK}/{timestamp}')
    news_entry.link(href=f'{FEED_LINK}/{timestamp}')
    news_entry.title(f'{time_period} {FEED_TITLE} - {date_str}')
    news_entry.description(markdown.markdown(news_content))
    
    logger.info(f'Successfully added {time_period.lower()} news entry for {date_str}')