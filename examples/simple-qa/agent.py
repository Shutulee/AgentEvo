"""简单问答 Demo - Agent 实现"""

import os
from pathlib import Path
from openai import OpenAI


def run(query: str, context: dict = None) -> str:
    """
    简单问答 Agent
    
    Args:
        query: 用户输入
        context: 可选上下文
        
    Returns:
        Agent 响应
    """
    # 读取系统提示词
    prompt_file = Path(__file__).parent / "system_prompt.md"
    system_prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
    
    # 调用 OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
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
