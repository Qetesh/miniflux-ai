import logging
from yaml import safe_load

config = safe_load(open('config.yml', encoding='utf8'))
logger = logging.getLogger(__name__)
logger.setLevel(config.get('log_level', 'INFO'))
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)
