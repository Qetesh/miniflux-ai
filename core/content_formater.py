import re
import markdown
from typing import Dict, Tuple
from markdownify import markdownify as md

from common import config

MARKER = '<div data-ai-agent="{}" style="display: none;"></div>'
MARKER_PATTERN = r'<div data-ai-agent="([^"]+)" style="display: none;"></div>'


def to_markdown(content: str) -> str:
    """
    Convert content to markdown format
    
    Args:
        content: Raw content (HTML or plain text)
        
    Returns:
        Markdown formatted content
    """
    return md(content)


def to_html(content: str) -> str:
    """
    Convert markdown formatted content to HTML format
    
    Args:
        content: Markdown formatted content
        
    Returns:
        HTML formatted content
    """
    return markdown.markdown(content)


def parse_entry_content(content: str) -> Tuple[str, Dict[str, str]]:
    """
    Parse entry content to extract original content and existing agent results
    
    Args:
        content: Full content including agent results and markers
        
    Returns:
        Tuple of (original_content, existing_agent_content_dict)
    """

    matches = list(re.finditer(MARKER_PATTERN, content))
    
    if not matches:
        return content, {}
    
    agent_results = {}
    
    for i, match in enumerate(matches):
        agent_name = match.group(1)
        start_pos = match.start()
        
        # Extract content before this marker
        if i == 0:
            # First agent - content is from beginning to marker
            agent_result = content[:start_pos].strip()
        else:
            # Other agents - content is from previous marker end to current marker
            prev_marker_end = matches[i - 1].end()
            agent_result = content[prev_marker_end:start_pos].strip()
        
        if agent_result:
            agent_results[agent_name] = agent_result
    
    # Extract original content (after the last marker)
    last_marker_end = matches[-1].end()
    original_content = content[last_marker_end:].strip()
    
    return original_content, agent_results


def build_ordered_content(agent_results: Dict[str, str], original_content: str) -> str:
    """
    Build final content with agent results in proper order
    
    Args:
        agent_results: Dictionary of agent_name to content
        original_content: Original article content
        
    Returns:
        Final ordered content string
    """
    if not agent_results:
        return original_content
    
    ordered_parts = []
    
    for agent_name in config.agents.keys():
        if agent_name in agent_results:
            ordered_parts.append(agent_results[agent_name])
            ordered_parts.append(MARKER.format(agent_name))
    
    ordered_parts.append(original_content)
    
    return ''.join(ordered_parts)
