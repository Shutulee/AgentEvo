"""init 命令 / Init command"""

from pathlib import Path
from rich.console import Console
from agent_evo.utils.i18n import t

console = Console()

# 默认配置模板 / Default config template
DEFAULT_CONFIG = """# AgentEvo 配置文件 / AgentEvo Configuration
version: "1"

# 被测 Agent 配置 / Agent under test configuration
agent:
  module: "agent"           # Agent 入口模块 / Agent entry module
  function: "run"           # Agent 入口函数 / Agent entry function
  prompt_file: "./system_prompt.md"  # 系统提示词文件 / System prompt file

# 测试用例路径 / Test cases path
test_cases: "./tests/*.yaml"

# LLM 配置 / LLM configuration
llm:
  provider: "openai"
  model: "gpt-4o"
  api_key: "${OPENAI_API_KEY}"

# 评判配置（因子化评测）/ Judge configuration (factor-based evaluation)
judge:
  pass_threshold: 0.7
  factors:
    structure:              # 结构正确性（JSON Schema、JSONPath）/ Structural correctness
      weight: 1.0
      fatal: true           # 致命因子：不通过则整条用例失败 / Fatal factor: case fails if not passed
    behavior:               # 行为正确性（工具调用、行为模式）/ Behavioral correctness
      weight: 0.8
      fatal: false
    content:                # 内容质量（关键词、语义标准）/ Content quality
      weight: 0.5
      fatal: false
    custom:                 # 自定义校验 / Custom validation
      weight: 1.0
      fatal: true

# Tag 策略：为不同标签设置独立的通过门禁 / Tag policies: set independent pass thresholds per tag
tag_policies:
  safety:
    pass_threshold: 1.0
    fail_fast: true
    required_for_release: true
  core:
    pass_threshold: 0.8
    required_for_release: true

# 优化配置 / Optimization configuration
optimization:
  max_iterations: 3
  run_regression: true
  regression_threshold: 0.95

# 变异扩充配置 / Mutation expansion configuration
mutation:
  count_per_case: 3
  auto_review: true

# 导入配置 / Import configuration
import:
  default_format: "jsonl"
  auto_refine: true
  default_tier: "silver"
  default_tags: ["regression"]

# Git 集成 / Git integration
git:
  enabled: true
  auto_commit: false
  create_pr: true
  pr_base_branch: "main"

# 报告语言 / Report language: zh (中文) or en (English)
language: "zh"
"""

# 默认 Agent 模板 / Default Agent template
DEFAULT_AGENT = '''"""示例 Agent / Example Agent"""

from pathlib import Path


def run(query: str, context: dict = None) -> str:
    """
    Agent 入口函数 / Agent entry function
    
    Args:
        query: 用户输入 / User input
        context: 可选上下文 / Optional context
        
    Returns:
        Agent 响应 / Agent response
    """
    # 读取系统提示词 / Read system prompt
    prompt_file = Path(__file__).parent / "system_prompt.md"
    system_prompt = prompt_file.read_text() if prompt_file.exists() else ""
    
    # TODO: 实现你的 Agent 逻辑 / Implement your Agent logic
    # 这里只是一个示例，你需要替换为实际的 LLM 调用
    # This is just an example, replace with actual LLM calls
    
    # 示例：简单回显 / Example: simple echo
    return f"收到你的问题: {query}"
'''

# 默认系统提示词模板 / Default system prompt template
DEFAULT_PROMPT = """# 系统提示词 / System Prompt

你是一个有帮助的 AI 助手。
You are a helpful AI assistant.

## 任务 / Task
回答用户的问题，提供准确、有用的信息。
Answer user questions and provide accurate, useful information.

## 要求 / Requirements
1. 回答要准确、完整 / Answers should be accurate and complete
2. 语言要清晰、易懂 / Language should be clear and understandable
3. 如果不确定，要诚实地说明 / If uncertain, be honest about it
"""

# 默认测试用例模板 / Default test cases template
DEFAULT_TEST_CASES = """# 基础功能测试 / Basic functionality tests
name: "基础功能测试 / Basic Tests"
description: "测试 Agent 的基础功能 / Test basic Agent functionality"

cases:
  - id: "basic-001"
    name: "简单问答 / Simple Q&A"
    input: "你好，请介绍一下你自己"
    expected_output: "你好！我是一个有帮助的 AI 助手，可以回答你的各种问题。"
    expected:
      contains: ["AI", "助手"]
    tags: ["core"]

  - id: "basic-002"
    name: "知识问答 / Knowledge Q&A"
    input: "什么是人工智能？"
    expected_output: "人工智能(AI)是计算机科学的一个分支，致力于创建能够模拟人类智能行为的系统，包括机器学习、自然语言处理等技术。"
    expected:
      contains: ["人工智能", "AI"]
    tags: ["core"]

  - id: "edge-001"
    name: "空输入处理 / Empty input handling"
    input: ""
    expected_output: "您好！看起来您还没有输入问题。请告诉我您想了解什么，我会尽力帮助您。"
    tags: ["edge"]
"""


def run_init(path: str, template: str):
    """初始化 AgentEvo 项目 / Initialize AgentEvo project"""
    project_dir = Path(path).resolve()
    
    console.print(f"\n[bold blue]🚀 {t('init_project')}: {project_dir}[/bold blue]\n")
    
    # 创建目录结构 / Create directory structure
    (project_dir / "tests").mkdir(parents=True, exist_ok=True)
    
    # 创建配置文件 / Create config file
    config_file = project_dir / "agent-evo.yaml"
    if not config_file.exists():
        config_file.write_text(DEFAULT_CONFIG, encoding="utf-8")
        console.print(f"  ✅ {t('init_created')}: agent-evo.yaml")
    else:
        console.print(f"  ⏭  {t('init_exists')}: agent-evo.yaml")
    
    # 创建示例 Agent / Create example Agent
    agent_file = project_dir / "agent.py"
    if not agent_file.exists():
        agent_file.write_text(DEFAULT_AGENT, encoding="utf-8")
        console.print(f"  ✅ {t('init_created')}: agent.py")
    else:
        console.print(f"  ⏭  {t('init_exists')}: agent.py")
    
    # 创建系统提示词 / Create system prompt
    prompt_file = project_dir / "system_prompt.md"
    if not prompt_file.exists():
        prompt_file.write_text(DEFAULT_PROMPT, encoding="utf-8")
        console.print(f"  ✅ {t('init_created')}: system_prompt.md")
    else:
        console.print(f"  ⏭  {t('init_exists')}: system_prompt.md")
    
    # 创建测试用例 / Create test cases
    test_file = project_dir / "tests" / "basic.yaml"
    if not test_file.exists():
        test_file.write_text(DEFAULT_TEST_CASES, encoding="utf-8")
        console.print(f"  ✅ {t('init_created')}: tests/basic.yaml")
    else:
        console.print(f"  ⏭  {t('init_exists')}: tests/basic.yaml")
    
    console.print(f"\n[bold green]✅ {t('init_done')}[/bold green]")
    console.print(f"\n{t('init_next_steps')}:")
    console.print(f"  1. {t('init_step_agent')}")
    console.print(f"  2. {t('init_step_prompt')}")
    console.print(f"  3. {t('init_step_tests')}")
    console.print(f"  4. {t('init_step_eval')}")
    console.print(f"  5. {t('init_step_run')}\n")
