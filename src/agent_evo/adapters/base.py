"""适配器基类 / Adapter base class"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class AgentAdapter(ABC):
    """Agent 适配器基类 / Agent adapter base class"""

    @abstractmethod
    async def invoke(self, input: str, context: Optional[dict[str, Any]] = None) -> str:
        """
        调用 Agent / Invoke the Agent

        Args:
            input: 用户输入 / User input
            context: 可选上下文 / Optional context

        Returns:
            Agent 输出 / Agent output
        """
        pass

    @abstractmethod
    def get_prompt_file(self) -> Optional[str]:
        """
        获取提示词文件路径 / Get prompt file path

        Returns:
            提示词文件路径，如果不支持则返回 None
            Prompt file path, or None if not supported
        """
        pass

    @abstractmethod
    async def update_prompt(self, new_content: str) -> None:
        """
        更新提示词 / Update prompt

        Args:
            new_content: 新的提示词内容 / New prompt content
        """
        pass
