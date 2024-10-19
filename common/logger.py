import logging
from .config import Config
config = Config()

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)
