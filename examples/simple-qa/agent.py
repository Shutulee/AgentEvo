"""简单问答 Demo - Agent 实现"""

import os
from pathlib import Path
from openai import OpenAI


def run(query: str, context: dict = None) -> str:
    """
    简单问答 Agent
    
    Args:
        query: 用户输入
        context: 可选上下文（框架会自动注入 llm 配置）
        
    Returns:
        Agent 响应
    """
    # 读取系统提示词
    prompt_file = Path(__file__).parent / "system_prompt.md"
    system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
    
    # 从 context 获取 LLM 配置（由框架从 agent-evo.yaml 自动注入）
    llm = (context or {}).get("llm", {})
    
    client = OpenAI(
        api_key=llm.get("api_key", os.environ.get("OPENAI_API_KEY")),
        base_url=llm.get("base_url"),
    )
    
    response = client.chat.completions.create(
        model=llm.get("model", "gpt-4o"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content or ""


if __name__ == "__main__":
    # 测试
    print(run("什么是人工智能？"))
