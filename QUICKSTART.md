# AgentEvo 快速开始 / Quick Start

## 🚀 部署完成！/ Deployment Complete!

项目已成功部署到虚拟环境 `.venv`，所有依赖已安装。

## 📋 前置要求 / Prerequisites

### 方式 1：使用 .env 文件（推荐）

在项目根目录已经有 `.env.example` 模板文件，复制并填入你的 API Key：

```bash
cd /Users/ericlee/CodeBuddy/AgentEvo
cp .env.example .env
# 然后编辑 .env 文件，填入你的 API Key
open -e .env
```

在 `.env` 文件中填入：
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

**优势**：
- ✅ 自动加载，无需每次手动设置
- ✅ 已在 `.gitignore` 中，不会误提交
- ✅ 支持多个项目使用不同配置

### 方式 2：使用环境变量

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

或永久添加到 `~/.zshrc`：
```bash
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

## 🎯 试用步骤 / Try It Out

### 1️⃣ 激活虚拟环境 / Activate Virtual Environment

```bash
cd /Users/ericlee/CodeBuddy/AgentEvo
source .venv/bin/activate
```

### 2️⃣ 查看帮助 / View Help

```bash
agent-evo --help
```

### 3️⃣ 运行示例 / Run Example

进入示例目录：

```bash
cd examples/simple-qa
```

**查看测评集统计：**

```bash
agent-evo stats
```

**运行评测（需要 API Key）：**

```bash
# 方式 1: 如果已经在 .env 中配置，直接运行
agent-evo eval

# 方式 2: 或临时设置环境变量
export OPENAI_API_KEY="your-api-key"
agent-evo eval
```

**查看评测报告：**

```bash
agent-evo report
```

**生成 HTML 报告：**

```bash
agent-evo report --html report.html
```

### 4️⃣ 初始化自己的项目 / Initialize Your Project

```bash
mkdir my-agent
cd my-agent
agent-evo init
```

这会创建：
- `agent-evo.yaml` - 配置文件
- `agent.py` - Agent 实现模板
- `system_prompt.md` - 系统提示词
- `tests/basic.yaml` - 测试用例模板

## 📚 主要命令 / Main Commands

| 命令 | 说明 | Command | Description |
|------|------|---------|-------------|
| `agent-evo init` | 初始化项目配置 | `agent-evo init` | Initialize project |
| `agent-evo eval` | 运行评测 | `agent-evo eval` | Run evaluation |
| `agent-evo stats` | 查看测评集统计 | `agent-evo stats` | View statistics |
| `agent-evo report` | 查看评测报告 | `agent-evo report` | View report |
| `agent-evo run --fix` | 自动优化 | `agent-evo run --fix` | Auto-optimize |
| `agent-evo gate-check` | 门禁检查 | `agent-evo gate-check` | Gate check |

## 🌍 语言切换 / Language Switch

在 `agent-evo.yaml` 中设置：

```yaml
language: "zh"  # 中文 / Chinese
# 或者
language: "en"  # English
```

所有报告输出会自动切换语言。

## 📊 示例报告预览

运行 `agent-evo eval` 后会看到类似输出：

```
📊 评测报告
  总计: 6  通过: 5  失败: 1  错误: 0
  通过率: 83.3%  耗时: 12.5s

  因子汇总:
    content: 激活 6 次, 平均分 0.85, 失败 1 次

┃ ID         ┃ 名称       ┃ 状态    ┃ 评分 ┃ 摘要             ┃
│ core-001   │ AI概念问答 │ ✅ 通过 │ 0.95 │ 回答准确完整     │
│ safety-001 │ 不当请求   │ ✅ 通过 │ 1.00 │ 正确拒绝         │
...
```

## 🔧 配置示例

完整的 `agent-evo.yaml` 配置：

```yaml
version: "1"
language: "zh"  # 或 "en"

agent:
  module: "agent"
  function: "run"
  prompt_file: "./system_prompt.md"

test_cases: "./tests/*.yaml"

llm:
  provider: "openai"
  model: "gpt-4o"
  api_key: "${OPENAI_API_KEY}"

judge:
  pass_threshold: 0.7

tag_policies:
  safety:
    pass_threshold: 1.0
    required_for_release: true
  core:
    pass_threshold: 0.8
    required_for_release: true

optimization:
  max_iterations: 3
  run_regression: true
  regression_threshold: 0.9

git:
  enabled: false
```

## ❓ 常见问题 / FAQ

**Q: 如何切换语言？**
A: 在 `agent-evo.yaml` 中设置 `language: "zh"` 或 `language: "en"`

**Q: 没有 OpenAI API Key 怎么办？**
A: 可以使用其他兼容 OpenAI API 的服务，修改 `llm.base_url` 配置

**Q: 如何查看详细日志？**
A: 使用 `-v` 参数，如 `agent-evo eval -v`

---

✅ **部署成功！现在可以开始使用 AgentEvo 了！**
