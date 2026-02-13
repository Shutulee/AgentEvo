"""init 命令"""

from pathlib import Path
from rich.console import Console

console = Console()

# 默认配置模板
DEFAULT_CONFIG = """# AgentEvo 配置文件
version: "1"

# 被测 Agent 配置
agent:
  module: "agent"           # Agent 入口模块
  function: "run"           # Agent 入口函数
  prompt_file: "./system_prompt.md"  # 系统提示词文件

# 测试用例路径
test_cases: "./tests/*.yaml"

# LLM 配置
llm:
  provider: "openai"
  model: "gpt-4o"
  api_key: "${OPENAI_API_KEY}"

# 评判配置（因子化评测）
judge:
  pass_threshold: 0.7
  factors:
    structure:              # 结构正确性（JSON Schema、JSONPath）
      weight: 1.0
      fatal: true           # 致命因子：不通过则整条用例失败
    behavior:               # 行为正确性（工具调用、行为模式）
      weight: 0.8
      fatal: false
    content:                # 内容质量（关键词、语义标准）
      weight: 0.5
      fatal: false
    custom:                 # 自定义校验
      weight: 1.0
      fatal: true

# Tag 策略：为不同标签设置独立的通过门禁
tag_policies:
  safety:
    pass_threshold: 1.0
    fail_fast: true
    required_for_release: true
  core:
    pass_threshold: 0.8
    required_for_release: true

# 诊断配置
diagnosis:
  confidence_threshold: 0.8
  categories:
    - id: "PROMPT_ISSUE"
      description: "提示词缺陷"
      auto_fix: true
    - id: "CONTEXT_ISSUE"
      description: "上下文/知识不足"
      auto_fix: false
    - id: "EDGE_CASE"
      description: "边界场景"
      auto_fix: true

# 优化配置
optimization:
  max_iterations: 3
  run_regression: true
  regression_threshold: 0.95

# 变异扩充配置
mutation:
  count_per_case: 3
  auto_review: true

# 导入配置
import:
  default_format: "jsonl"
  auto_refine: true
  default_tier: "silver"
  default_tags: ["regression"]

# Git 集成
git:
  enabled: true
  auto_commit: false
  create_pr: true
  pr_base_branch: "main"
"""

# 默认 Agent 模板
DEFAULT_AGENT = '''"""示例 Agent"""

from pathlib import Path


def run(query: str, context: dict = None) -> str:
    """
    Agent 入口函数
    
    Args:
        query: 用户输入
        context: 可选上下文
        
    Returns:
        Agent 响应
    """
    # 读取系统提示词
    prompt_file = Path(__file__).parent / "system_prompt.md"
    system_prompt = prompt_file.read_text() if prompt_file.exists() else ""
    
    # TODO: 实现你的 Agent 逻辑
    # 这里只是一个示例，你需要替换为实际的 LLM 调用
    
    # 示例：简单回显
    return f"收到你的问题: {query}"
'''

# 默认系统提示词模板
DEFAULT_PROMPT = """# 系统提示词

你是一个有帮助的 AI 助手。

## 任务
回答用户的问题，提供准确、有用的信息。

## 要求
1. 回答要准确、完整
2. 语言要清晰、易懂
3. 如果不确定，要诚实地说明
"""

# 默认测试用例模板
DEFAULT_TEST_CASES = """# 基础功能测试
name: "基础功能测试"
description: "测试 Agent 的基础功能"

cases:
  - id: "basic-001"
    name: "简单问答"
    input: "你好，请介绍一下你自己"
    expected:
      contains: ["AI", "助手"]
    tags: ["core"]

  - id: "basic-002"
    name: "知识问答"
    input: "什么是人工智能？"
    expected:
      contains: ["人工智能", "AI", "机器"]
    tags: ["core"]

  - id: "edge-001"
    name: "空输入处理"
    input: ""
    expected:
      behavior: "ask_clarification"
      behavior_hint: "应该请求用户提供更多信息"
    tags: ["edge"]
"""


def run_init(path: str, template: str):
    """初始化 AgentEvo 项目"""
    project_dir = Path(path).resolve()
    
    console.print(f"\n[bold blue]🚀 初始化 AgentEvo 项目: {project_dir}[/bold blue]\n")
    
    # 创建目录结构
    (project_dir / "tests").mkdir(parents=True, exist_ok=True)
    
    # 创建配置文件
    config_file = project_dir / "agent-evo.yaml"
    if not config_file.exists():
        config_file.write_text(DEFAULT_CONFIG, encoding="utf-8")
        console.print(f"  ✅ 创建配置文件: agent-evo.yaml")
    else:
        console.print(f"  ⏭  配置文件已存在: agent-evo.yaml")
    
    # 创建示例 Agent
    agent_file = project_dir / "agent.py"
    if not agent_file.exists():
        agent_file.write_text(DEFAULT_AGENT, encoding="utf-8")
        console.print(f"  ✅ 创建示例 Agent: agent.py")
    else:
        console.print(f"  ⏭  Agent 文件已存在: agent.py")
    
    # 创建系统提示词
    prompt_file = project_dir / "system_prompt.md"
    if not prompt_file.exists():
        prompt_file.write_text(DEFAULT_PROMPT, encoding="utf-8")
        console.print(f"  ✅ 创建系统提示词: system_prompt.md")
    else:
        console.print(f"  ⏭  提示词文件已存在: system_prompt.md")
    
    # 创建测试用例
    test_file = project_dir / "tests" / "basic.yaml"
    if not test_file.exists():
        test_file.write_text(DEFAULT_TEST_CASES, encoding="utf-8")
        console.print(f"  ✅ 创建测试用例: tests/basic.yaml")
    else:
        console.print(f"  ⏭  测试用例已存在: tests/basic.yaml")
    
    console.print("\n[bold green]✅ 初始化完成！[/bold green]")
    console.print("\n下一步:")
    console.print("  1. 编辑 [cyan]agent.py[/cyan] 实现你的 Agent 逻辑")
    console.print("  2. 编辑 [cyan]system_prompt.md[/cyan] 定义系统提示词")
    console.print("  3. 编辑 [cyan]tests/basic.yaml[/cyan] 添加测试用例")
    console.print("  4. 运行 [cyan]agent-evo eval[/cyan] 开始评测")
    console.print("  5. 运行 [cyan]agent-evo run --fix[/cyan] 自动优化\n")
