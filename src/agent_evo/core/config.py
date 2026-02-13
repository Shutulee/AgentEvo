"""配置加载 / Configuration loader"""

import os
import re
from pathlib import Path
from typing import Optional

import yaml

from agent_evo.models.config import Config
from agent_evo.utils.i18n import set_language, t


def _resolve_env_vars(value: str) -> str:
    """解析环境变量 ${VAR} 格式 / Resolve ${VAR} environment variables"""
    pattern = r'\$\{([^}]+)\}'
    
    def replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    
    return re.sub(pattern, replace, value)


def _resolve_config_env_vars(config_dict: dict) -> dict:
    """递归解析配置中的环境变量 / Recursively resolve env vars in config"""
    result = {}
    for key, value in config_dict.items():
        if isinstance(value, str):
            result[key] = _resolve_env_vars(value)
        elif isinstance(value, dict):
            result[key] = _resolve_config_env_vars(value)
        elif isinstance(value, list):
            result[key] = [
                _resolve_config_env_vars(item) if isinstance(item, dict)
                else _resolve_env_vars(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def load_config(config_path: Optional[str] = None) -> Config:
    """
    加载配置文件 / Load configuration file

    Args:
        config_path: 配置文件路径，默认为 agent-evo.yaml / Config file path, defaults to agent-evo.yaml

    Returns:
        Config 对象 / Config object
    """
    if config_path is None:
        # 查找默认配置文件 / Look for default config file
        for name in ["agent-evo.yaml", "agent-evo.yml", ".agent-evo.yaml"]:
            if Path(name).exists():
                config_path = name
                break
        else:
            raise FileNotFoundError(
                t("config_not_found")
            )

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(t("config_file_missing").format(path=config_path))

    with open(config_file, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)

    # 解析环境变量 / Resolve environment variables
    config_dict = _resolve_config_env_vars(config_dict)

    config = Config(**config_dict)

    # 设置全局语言 / Set global language from config
    set_language(config.language)

    return config
