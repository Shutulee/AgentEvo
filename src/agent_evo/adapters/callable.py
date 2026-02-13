"""Callable 适配器"""

import asyncio
import inspect
from pathlib import Path
from typing import Any, Callable, Optional

from agent_evo.adapters.base import AgentAdapter


class CallableAdapter(AgentAdapter):
    """
    通用 Callable 适配器
    
    支持同步和异步函数
    """
    
    def __init__(
        self,
        func: Callable,
        prompt_file: Optional[str] = None
    ):
        """
        Args:
            func: Agent 入口函数，签名应为 (input: str, context: dict = None) -> str
            prompt_file: 系统提示词文件路径
        """
        self.func = func
        self._prompt_file = prompt_file
        self._is_async = asyncio.iscoroutinefunction(func)
    
    async def invoke(self, input: str, context: Optional[dict[str, Any]] = None) -> str:
        """调用 Agent"""
        # 检查函数签名，决定如何传参
        sig = inspect.signature(self.func)
        params = list(sig.parameters.keys())
        
        kwargs = {}
        if len(params) >= 1:
            # 第一个参数是 input
            kwargs[params[0]] = input
        if len(params) >= 2 and context is not None:
            # 第二个参数是 context
            kwargs[params[1]] = context
        
        if self._is_async:
            result = await self.func(**kwargs)
        else:
            # 在线程池中运行同步函数
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self.func(**kwargs))
        
        return str(result) if result is not None else ""
    
    def get_prompt_file(self) -> Optional[str]:
        """获取提示词文件路径"""
        return self._prompt_file
    
    async def update_prompt(self, new_content: str) -> None:
        """更新提示词"""
        if self._prompt_file:
            Path(self._prompt_file).write_text(new_content, encoding="utf-8")
