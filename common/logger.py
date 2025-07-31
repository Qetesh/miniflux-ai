import logging
from typing import Dict, Any
from .config import config

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)


def log_entry_debug(entry: Dict[str, Any], agent_name: str = None, message: str = "", 
                    include_title: bool = False, include_content: bool = False):
    _log_entry(entry, level="debug", agent_name=agent_name, message=message, include_title=include_title, include_content=include_content)


def log_entry_info(entry: Dict[str, Any], agent_name: str = None, message: str = "", 
                   include_title: bool = False, include_content: bool = False):
    _log_entry(entry, level="info", agent_name=agent_name, message=message, include_title=include_title, include_content=include_content)


def log_entry_warning(entry: Dict[str, Any], agent_name: str = None, message: str = "", 
                    include_title: bool = False, include_content: bool = False):
    _log_entry(entry, level="warning", agent_name=agent_name, message=message, include_title=include_title, include_content=include_content)


def log_entry_error(entry: Dict[str, Any], agent_name: str = None, message: str = "", 
                    include_title: bool = False, include_content: bool = False):
    _log_entry(entry, level="error", agent_name=agent_name, message=message, include_title=include_title, include_content=include_content)


def _log_entry(entry: Dict[str, Any], level: str = "info", agent_name: str = None, 
              message: str = "", include_title: bool = False, include_content: bool = False):
    """
    Unified logging method for entry processing with standardized format
    
    Args:
        entry: Entry dictionary
        agent_name: Agent name (optional)
        message: Log message
        level: Log level (info, debug, error)
        include_title: Whether to include entry title
        include_content: Whether to include entry content (debug only)
    """
    entry_id = entry.get('id', 'unknown')
    
    # Build log parts in order: entry_id, agent_name, message, entry_title, entry_content
    parts = [f"Entry {entry_id}"]
    
    if agent_name:
        parts.append(f"Agent {agent_name}")
    
    if include_title and entry.get('title'):
        entry_title = entry['title']
        if len(entry_title) > 100:
            entry_title = entry_title[:100] + "..."
        parts.append(f"Title: {entry_title}")

    if message:
        message_preview = message.replace("\n", "\\n")
        message_preview = message_preview[:1000] + "..." if len(message_preview) > 1000 else message_preview
        parts.append(message_preview)
    
    if include_content and level == "debug" and entry.get('content'):
        content = entry['content']
        content_preview = content.replace("\n", "\\n")
        content_preview = content_preview[:1000] + "..." if len(content_preview) > 1000 else content_preview  
        parts.append(f"Content: {content_preview}")
    
    log_message = " - ".join(parts)
    
    if level == "debug":
        logger.debug(log_message)
    elif level == "error":
        logger.error(log_message)
    elif level == "warning":
        logger.warning(log_message)
    else:
        logger.info(log_message)
