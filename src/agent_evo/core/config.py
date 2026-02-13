"""配置加载"""

import os
import re
from pathlib import Path
from typing import Optional

import yaml

from agent_evo.models.config import Config


def _resolve_env_vars(value: str) -> str:
    """解析环境变量 ${VAR} 格式"""
    pattern = r'\$\{([^}]+)\}'
    
    def replace(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    
    return re.sub(pattern, replace, value)


def _resolve_config_env_vars(config_dict: dict) -> dict:
    """递归解析配置中的环境变量"""
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
    加载配置文件
    
    Args:
        config_path: 配置文件路径，默认为 agent-evo.yaml
        
    Returns:
        Config 对象
    """
    if config_path is None:
        # 查找默认配置文件
        for name in ["agent-evo.yaml", "agent-evo.yml", ".agent-evo.yaml"]:
            if Path(name).exists():
                config_path = name
                break
        else:
            raise FileNotFoundError(
                "未找到配置文件。请运行 `agent-evo init` 初始化项目，"
                "或指定配置文件路径。"
            )
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_file, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)
    
    # 解析环境变量
    config_dict = _resolve_config_env_vars(config_dict)
    
    return Config(**config_dict)
