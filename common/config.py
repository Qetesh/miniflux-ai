import sys
import inspect
from yaml import safe_load

class Config:
    def __init__(self):
        with open('config.yml', encoding='utf8') as f:
            self.c = safe_load(f)
        
        self.log_level = self.c.get('log_level', 'INFO')
        self.entry_since = self.c.get('entry_since', 0)

        self.miniflux_base_url = self._get_config_value('miniflux', 'base_url', None)
        self.miniflux_api_key = self._get_config_value('miniflux', 'api_key', None)
        self.miniflux_webhook_secret = self._get_config_value('miniflux', 'webhook_secret', None)

        self.llm_base_url = self._get_config_value('llm', 'base_url', None)
        self.llm_api_key = self._get_config_value('llm', 'api_key', None)
        self.llm_model = self._get_config_value('llm', 'model', None)
        self.llm_timeout = self._get_config_value('llm', 'timeout', 60)
        self.llm_max_workers = self._get_config_value('llm', 'max_workers', 4)
        self.llm_RPM = self._get_config_value('llm', 'RPM', 1000)

        self.ai_news_url = self._get_config_value('ai_news', 'url', None)
        self.ai_news_schedule = self._get_config_value('ai_news', 'schedule', None)
        self.ai_news_prompts = self._get_config_value('ai_news', 'prompts', None)

        self.agents = self.c.get('agents', {})
        
        self._validate_config_compatibility()

    def _get_config_value(self, section, key, default=None):
        return self.c.get(section, {}).get(key, default)
    
    def _validate_config_compatibility(self):
        """
        Validate config file version compatibility.
        """
        if not self.agents:
            return
        
        outdated_agents = []
        
        for agent_name, agent_config in self.agents.items():
            if not isinstance(agent_config, dict):
                continue
            
            if 'title' in agent_config and 'style_block' in agent_config:
                outdated_agents.append(agent_name)
        
        if outdated_agents:
            error_message = inspect.cleandoc(f"""
            ⚠️  Config Incompatibility Detected!
            
            Your config.yml is using an outdated format that is no longer supported.
            This is a breaking change and requires configuration file update.
            
            Detected outdated agents: {', '.join(outdated_agents)}
            
            Please update your config.yml file to the new format.
            
            For migration guide and examples, please visit:
            https://github.com/Qetesh/miniflux-ai
            """)
            
            print(error_message)
            sys.exit(1)


config = Config()