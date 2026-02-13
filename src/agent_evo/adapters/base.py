"""适配器基类"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class AgentAdapter(ABC):
    """Agent 适配器基类"""
    
    @abstractmethod
    async def invoke(self, input: str, context: Optional[dict[str, Any]] = None) -> str:
        """
        调用 Agent
        
        Args:
            input: 用户输入
            context: 可选上下文
            
        Returns:
            Agent 输出
        """
        pass
    
    @abstractmethod
    def get_prompt_file(self) -> Optional[str]:
        """
        获取提示词文件路径
        
        Returns:
            提示词文件路径，如果不支持则返回 None
        """
        pass
    
    @abstractmethod
    async def update_prompt(self, new_content: str) -> None:
        """
        更新提示词
        
        Args:
            new_content: 新的提示词内容
        """
        pass
    

