import threading
from pathlib import Path

from .config import config
from .logger import logger


# File paths
SUMMARY_FILE = Path('ai_summaries.data')
AI_NEWS_FILE = Path('ai_news.data')

# Shared file lock for ai_summaries.data to prevent concurrent read/write issues
SUMMARY_FILE_LOCK = threading.Lock()
