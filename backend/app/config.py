# backend/app/config.py
import yaml
from typing import Dict, Any
import os
from .logger import logger

def load_config() -> Dict[str, Any]:
    """加载YAML配置文件。"""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"配置文件未找到: {config_path}")
        return {}
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}

settings = load_config()