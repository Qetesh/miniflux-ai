import fnmatch
from typing import Dict, List, Any

from common.logger import log_entry_debug


def filter_entry(agent: tuple, entry: Dict[str, Any]) -> bool:
    """
    Filter entry based on agent configuration and content processing status
    
    Args:
        config: Configuration object containing agents settings
        agent: Tuple containing agent name and configuration
        entry: Entry dictionary with content and feed information
        
    Returns:
        True if entry should be processed, False otherwise
    """
    agent_name, _ = agent
    if _is_already_processed(agent, entry):
        log_entry_debug(entry, agent_name=agent_name, message=f"Already processed, skipping")
        return False
    
    return _should_process_entry(agent, entry)


def _is_already_processed(agent: tuple, entry: Dict[str, Any]) -> bool:
    """
    Check if entry has already been processed by this specific agent
    
    Args:
        agent: Tuple containing agent name and configuration
        entry: Entry dictionary
        
    Returns:
        True if entry is already processed, False otherwise
    """
    agent_name, _ = agent
    marker = f"<div data-ai-agent=\"{agent_name}\" style=\"display: none;\"></div>"
    
    return marker in entry['content']


def _should_process_entry(agent: tuple, entry: Dict[str, Any]) -> bool:
    """
    Determine if entry should be processed based on allow/deny lists
    
    Args:
        agent: Tuple containing agent name and configuration
        entry: Entry dictionary
        
    Returns:
        True if entry should be processed, False otherwise
    """
    _, agent_config = agent
    site_url = entry['feed']['site_url']
    
    allow_list = agent_config.get('allow_list')
    deny_list = agent_config.get('deny_list')
    
    # If allow list exists, only process entries from allowed sites
    if allow_list is not None:
        return _matches_any_pattern(site_url, allow_list)
    
    # If deny list exists, process entries except from denied sites
    if deny_list is not None:
        return not _matches_any_pattern(site_url, deny_list)
    
    # If neither list exists, process all entries
    return True


def _matches_any_pattern(url: str, patterns: List[str]) -> bool:
    """
    Check if URL matches any of the given patterns
    
    Args:
        url: URL to check
        patterns: List of patterns to match against
        
    Returns:
        True if URL matches any pattern, False otherwise
    """
    return any(fnmatch.fnmatch(url, pattern) for pattern in patterns)
