"""适配器模块 / Adapter modules"""

from agent_evo.adapters.base import AgentAdapter
from agent_evo.adapters.callable import CallableAdapter
from agent_evo.adapters.http import HttpAdapter

__all__ = ["AgentAdapter", "CallableAdapter", "HttpAdapter"]
