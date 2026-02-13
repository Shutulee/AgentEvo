"""AgentEvo - LLM Agent 自动化评测与优化框架
AgentEvo - LLM Agent automated evaluation and optimization framework"""

__version__ = "0.1.0"

from agent_evo.core.pipeline import Pipeline
from agent_evo.core.config import Config

__all__ = ["Pipeline", "Config", "__version__"]
