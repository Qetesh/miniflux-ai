import json
import traceback
from typing import Dict, Any

from common.logger import logger, log_entry_debug, log_entry_info, log_entry_error
from common import config, SUMMARY_FILE_LOCK, SUMMARY_FILE
from core.entry_filter import filter_entry
from core.llm_client import get_completion
from core.content_formater import (
    to_markdown, 
    to_html, 
    parse_entry_content, 
    build_ordered_content
)


def process_entry(miniflux_client, entry: Dict[str, Any]) -> tuple[str, ...]:
    """
    Process a single entry through all configured agents
    
    Args:
        miniflux_client: Miniflux client instance
        entry: Entry dictionary to process
    """
    try:
        log_entry_debug(entry, message="Starting processing")
        
        # Parse entry content once to get original content and existing agent results
        original_content, existing_agent_results = parse_entry_content(entry['content'])

        if not original_content.strip():
            log_entry_debug(entry, message="Entry content is empty, skipping")
            return ()
        
        original_entry = entry.copy()
        original_entry['content'] = original_content
        log_entry_debug(original_entry, message="Parsed original content", include_title=False, include_content=True)
        
        if existing_agent_results:
            log_entry_debug(original_entry, message=f"Found existing agent results: {list(existing_agent_results.keys())}")
        
        # process entry with config.agents excluding keys in existing agent results
        agents_to_process = {k: v for k, v in config.agents.items() if k not in existing_agent_results.keys()}
        new_agent_results = _process_entry_with_agents(original_entry, agents_to_process)
        
        if new_agent_results:
            # Combine existing and new agent results, then update entry
            all_agent_results = {**existing_agent_results, **new_agent_results}
            final_content = build_ordered_content(all_agent_results, original_content)
            
            miniflux_client.update_entry(entry['id'], content=final_content)
            log_entry_info(entry, message=f"Updated successfully with new agent results: {list(new_agent_results.keys())}")
        else:
            log_entry_debug(entry, message="No new agent results generated, entry unchanged")

        return tuple(new_agent_results.keys())
            
    except Exception as e:
        log_entry_error(entry, message=f"Processing failed: {e}")
        raise


def _process_entry_with_agents(entry: Dict[str, Any], agents: Dict[str, Any]) -> Dict[str, str]:
    """
    Process entry through all applicable agents
    
    Args:
        entry: Entry dictionary to process
        
    Returns:
        Dictionary of agent_name: agent_result
    """
    agent_results = {}
    
    # config.agents is ordered, required Python 3.7+
    for agent_name, agent_config in agents.items():
        agent = (agent_name, agent_config)
        
        agent_result = _process_with_single_agent(agent, entry)
        
        if agent_result:
            agent_results[agent_name] = agent_result
            
    return agent_results


def _process_with_single_agent(agent: tuple, entry: Dict[str, Any]) -> str:
    """
    Process entry with a single agent
    
    Args:
        agent: Tuple of (agent_name, agent_config)
        entry: Entry dictionary to process
        
    Returns:
        Formatted result content
    """
    agent_name, agent_config = agent
    log_entry_debug(entry, agent_name=agent_name, message="Starting processing")

    if not filter_entry(agent, entry):
        log_entry_debug(entry, agent_name=agent_name, message="Filtered out")
        return ""
    
    try:
        agent_content = _get_agent_content(agent, entry)
        log_entry_info(entry, agent_name=agent_name, message=f'Result: {agent_content}', include_title=True)

        if config.ai_news_schedule and agent_name == 'summary':
            # save summary to file for ai_news feature
            _save_summary_entry(entry, agent_content)

        formatted_result = _format_agent_result(agent_config, agent_content)
        log_entry_debug(entry, agent_name=agent_name, message=formatted_result, include_title=True)
        
        return formatted_result
        
    except Exception as e:
        log_entry_error(entry, agent_name=agent_name, message=f"Processing failed: {e}")
        logger.error(traceback.format_exc())
        return ""


def _get_agent_content(agent: tuple, entry: Dict[str, Any]) -> str:
    """
    Get processed content from LLM for a specific agent
    
    Args:
        agent: Tuple of (agent_name, agent_config)
        entry: Entry dictionary to process
        
    Returns:
        str: Processed content from LLM
    """
    agent_name, agent_config = agent
    prompt = agent_config['prompt']
    content_markdown = to_markdown(entry['content'])
    
    if '${content}' in prompt:
        system_prompt = "You are a helpful assistant."
        user_prompt = prompt.replace('${content}', content_markdown)
    else:
        system_prompt = prompt
        user_prompt = content_markdown

    log_entry_debug(entry, agent_name=agent_name, message=f"LLM request sent: system_prompt: {system_prompt}; user_prompt: {user_prompt}")

    agent_content = get_completion(system_prompt, user_prompt)
    
    log_entry_debug(entry, agent_name=agent_name, message=f"LLM response received: {agent_content}")
    return agent_content


def _format_agent_result(agent_config: Dict[str, Any], agent_content: str) -> str:
    """
    Format agent result based on style configuration
    
    Args:
        agent_config: Agent configuration dictionary
        agent_content: Raw response from LLM
        
    Returns:
        Formatted content string
    """
    template = agent_config.get('template', '')
    html_content = to_html(agent_content)
    
    if template:
        return template.replace('${content}', html_content)
    else:
        return html_content


def _save_summary_entry(entry: Dict[str, Any], summary_content: str) -> None:
    """
    Save summary entry to JSONL file for ai_summary feature
    Each line contains one JSON object for better performance
    
    Args:
        entry: Original entry dictionary
        summary_content: Processed summary content
    """
    if not summary_content:
        return
    
    entry_data = {
        'datetime': entry['created_at'],
        'category': entry['feed']['category']['title'],
        'title': entry['title'],
        'content': summary_content
    }
    
    with SUMMARY_FILE_LOCK:
        try:
            with open(SUMMARY_FILE, 'a', encoding='utf-8') as file:
                json_line = json.dumps(entry_data, ensure_ascii=False)
                file.write(json_line + '\n')
                
        except Exception as e:
            log_entry_error(entry, message=f"Failed to save summary: {e}")
            logger.error(traceback.format_exc())
