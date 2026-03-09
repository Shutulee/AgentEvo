"""HTTP 适配器 / HTTP adapter

通过 HTTP API 调用远程 Agent 服务，支持普通 JSON 响应和 SSE 流式响应。
Call remote Agent service via HTTP API, supports both JSON and SSE streaming responses.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import httpx

from agent_evo.adapters.base import AgentAdapter


def _resolve_env_vars(value: str) -> str:
    """解析字符串中的 ${ENV_VAR} 占位符 / Resolve ${ENV_VAR} placeholders in string"""
    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return re.sub(r"\$\{(\w+)\}", _replace, value)


def _resolve_deep(obj: Any) -> Any:
    """递归解析对象中所有字符串的环境变量 / Recursively resolve env vars in all strings"""
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    if isinstance(obj, dict):
        return {k: _resolve_deep(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_deep(item) for item in obj]
    return obj


def _get_by_path(data: Any, path: str) -> Any:
    """通过点分路径从嵌套字典中提取值 / Extract value from nested dict by dot-separated path

    例如 "data.outputs.output" 会依次访问 data["data"]["outputs"]["output"]
    """
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            raise KeyError(f"Cannot traverse path '{path}' at '{part}', current type: {type(current)}")
    return current


def _build_request_body(template: dict[str, Any], input_text: str, context: Optional[dict[str, Any]]) -> dict:
    """根据模板构建请求体，替换 ${input} 和 ${context.*} 占位符
    Build request body from template, replacing ${input} and ${context.*} placeholders
    """
    def _substitute(obj: Any) -> Any:
        if isinstance(obj, str):
            # 完整字符串替换 / Whole string replacement
            if obj == "${input}":
                return input_text
            if obj.startswith("${context.") and obj.endswith("}"):
                key = obj[10:-1]  # 去掉 ${context. 和 }
                return (context or {}).get(key, obj)
            # 内联替换 / Inline replacement
            result = obj.replace("${input}", input_text)
            if context:
                for k, v in context.items():
                    result = result.replace(f"${{context.{k}}}", str(v))
            return _resolve_env_vars(result)
        if isinstance(obj, dict):
            return {k: _substitute(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_substitute(item) for item in obj]
        return obj

    return _substitute(template)


class HttpAdapter(AgentAdapter):
    """
    HTTP 适配器 / HTTP adapter

    通过 HTTP API 调用远程部署的 Agent，支持:
    - 普通 JSON 响应（从响应中按路径提取结果）
    - SSE 流式响应（自动拼接 text 事件，或从 done 事件取最终结果）

    Calls remotely deployed Agent via HTTP API, supports:
    - Regular JSON response (extract result by path)
    - SSE streaming response (auto-concatenate text events, or use done event)
    """

    def __init__(
        self,
        url: str,
        method: str = "POST",
        headers: Optional[dict[str, str]] = None,
        body_template: Optional[dict[str, Any]] = None,
        response_path: Optional[str] = None,
        stream: bool = False,
        stream_event_field: str = "event",
        stream_content_field: str = "content",
        stream_done_event: str = "done",
        stream_text_events: Optional[list[str]] = None,
        timeout: float = 120.0,
        prompt_file: Optional[str] = None,
    ):
        """
        Args:
            url: API 地址 / API URL
            method: HTTP 方法 / HTTP method
            headers: 请求头（支持 ${ENV_VAR}）/ Request headers (supports ${ENV_VAR})
            body_template: 请求体模板（支持 ${input} 占位符）/ Request body template
            response_path: 非流式响应中结果的 JSON 路径 / JSON path for result in non-streaming response
            stream: 是否为 SSE 流式接口 / Whether it's an SSE streaming endpoint
            stream_event_field: SSE JSON 中事件类型字段名 / Event type field name in SSE JSON
            stream_content_field: SSE JSON 中内容字段名 / Content field name in SSE JSON
            stream_done_event: SSE 完成事件名 / SSE done event name
            stream_text_events: SSE 中视为文本输出的事件类型 / Event types treated as text output
            timeout: 请求超时（秒）/ Request timeout in seconds
            prompt_file: 本地提示词文件路径（可选）/ Local prompt file path (optional)
        """
        self._url = url
        self._method = method.upper()
        self._headers = headers or {}
        self._body_template = body_template or {"input": "${input}"}
        self._response_path = response_path
        self._stream = stream
        self._stream_event_field = stream_event_field
        self._stream_content_field = stream_content_field
        self._stream_done_event = stream_done_event
        self._stream_text_events = stream_text_events or ["text"]
        self._timeout = timeout
        self._prompt_file = prompt_file

    async def invoke(self, input: str, context: Optional[dict[str, Any]] = None) -> str:
        """调用远程 Agent / Call remote Agent"""
        url = _resolve_env_vars(self._url)
        headers = {k: _resolve_env_vars(v) for k, v in self._headers.items()}
        body = _build_request_body(self._body_template, input, context)

        if self._stream:
            return await self._invoke_stream(url, headers, body)
        else:
            return await self._invoke_json(url, headers, body)

    async def _invoke_json(self, url: str, headers: dict, body: dict) -> str:
        """非流式 JSON 请求 / Non-streaming JSON request"""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                method=self._method,
                url=url,
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        if self._response_path:
            result = _get_by_path(data, self._response_path)
        else:
            result = data

        return str(result) if result is not None else ""

    async def _invoke_stream(self, url: str, headers: dict, body: dict) -> str:
        """SSE 流式请求 / SSE streaming request"""
        chunks: list[str] = []
        done_content: Optional[str] = None

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                method=self._method,
                url=url,
                headers=headers,
                json=body,
            ) as response:
                response.raise_for_status()

                buffer = ""
                async for raw_chunk in response.aiter_text():
                    buffer += raw_chunk

                    # 解析 SSE 行 / Parse SSE lines
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line:
                            continue

                        # 处理标准 SSE "data: {...}" 格式
                        # Handle standard SSE "data: {...}" format
                        if line.startswith("data:"):
                            payload = line[5:].strip()
                        else:
                            payload = line

                        if not payload or payload == "[DONE]":
                            continue

                        try:
                            event_data = json.loads(payload)
                        except json.JSONDecodeError:
                            continue

                        event_type = event_data.get(self._stream_event_field, "")

                        if event_type == self._stream_done_event:
                            # done 事件：如果有 content 字段且 cover=true，则用 done 的内容
                            dc = event_data.get(self._stream_content_field)
                            cover = event_data.get("cover", False)
                            if dc is not None and cover:
                                done_content = str(dc)
                            elif dc is not None:
                                done_content = str(dc)
                            break
                        elif event_type == "error":
                            msg = event_data.get("message", "Unknown error")
                            code = event_data.get("code", 500)
                            raise RuntimeError(f"Agent returned error (code={code}): {msg}")
                        elif event_type in self._stream_text_events:
                            content = event_data.get(self._stream_content_field, "")
                            if content:
                                chunks.append(str(content))

        # 优先使用 done 事件的完整内容 / Prefer done event's full content
        if done_content is not None:
            return done_content
        return "".join(chunks)

    def get_prompt_file(self) -> Optional[str]:
        """获取提示词文件路径 / Get prompt file path"""
        return self._prompt_file

    async def update_prompt(self, new_content: str) -> None:
        """更新提示词 / Update prompt

        HTTP 适配器场景下，prompt 在远端服务中，本地文件仅作参考。
        In HTTP adapter scenario, prompt is on the remote service, local file is for reference only.
        """
        if self._prompt_file:
            Path(self._prompt_file).write_text(new_content, encoding="utf-8")
