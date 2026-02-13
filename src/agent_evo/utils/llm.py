"""LLM 调用封装 / LLM call wrapper"""

import os
from typing import Any, Optional

from agent_evo.models.config import LLMConfig


class LLMClient:
    """LLM 客户端 / LLM client"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
    
    def _get_client(self):
        """延迟初始化客户端 / Lazy-initialize the client"""
        if self._client is None:
            if self.config.provider == "openai":
                from openai import AsyncOpenAI
                
                api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY")
                base_url = self.config.base_url
                
                self._client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
            else:
                raise ValueError(f"不支持的 LLM 提供商 / Unsupported LLM provider: {self.config.provider}")
        
        return self._client
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: Optional[dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """
        发送聊天请求 / Send chat request
        
        Args:
            messages: 消息列表 / Message list
            response_format: 响应格式（如 {"type": "json_object"}）/ Response format
            temperature: 温度 / Temperature
            max_tokens: 最大 token 数 / Maximum token count
            
        Returns:
            响应内容 / Response content
        """
        client = self._get_client()
        
        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = await client.chat.completions.create(**kwargs)
        
        return response.choices[0].message.content or ""
