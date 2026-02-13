---
name: agent-development-guide
description: |
  LLM Agent 开发规范与最佳实践指南。
  当用户开发 AI Agent、设计评测框架、或进行 Prompt 优化时触发此 skill。
  典型触发场景包括：
  - 用户说"帮我设计一个 Agent"
  - 用户说"如何评测 Agent 的效果"
  - 用户说"Agent 的架构应该怎么设计"
  - 用户询问"如何优化 Prompt"或"Agent 开发有什么最佳实践"
  此 skill 提供行业最佳实践、竞品分析和设计模式参考。
---

# LLM Agent 开发规范与最佳实践

## 概述

本 skill 汇总了 Anthropic、OpenAI 等头部厂商的 Agent 开发规范，以及 promptfoo、LangSmith 等评测框架的设计理念，为 Agent 开发提供系统性指导。

---

## 核心原则（来自 Anthropic "Building Effective Agents"）

### 1. 保持简单性（Simplicity First）

> **核心观点**: 不要过度设计，能用简单 Prompt 解决的问题不要用复杂 Agent。

- **从简单开始**: 先用单个 LLM 调用 + 良好 Prompt 尝试
- **逐步增加复杂性**: 只在确实需要时才引入 Agent 架构
- **避免框架依赖**: 优先使用原生 API，减少不必要的抽象层

```
复杂度阶梯（从低到高）:
1. 单次 LLM 调用 + Prompt Engineering
2. LLM + 检索增强 (RAG)
3. LLM + 工具调用 (Function Calling)
4. 工作流编排 (Workflow/Chain)
5. 自主 Agent (Autonomous Agent)
```

### 2. Agent vs Workflow 的选择

| 维度 | Workflow | Agent |
|------|----------|-------|
| 定义 | 预定义的固定步骤流程 | LLM 动态决策下一步行动 |
| 适用场景 | 任务明确、步骤固定 | 任务开放、需要探索 |
| 可预测性 | 高 | 低 |
| 调试难度 | 低 | 高 |
| 推荐度 | 优先选择 | 必要时使用 |

**选择建议**:
- 能用 Workflow 解决的 → 用 Workflow
- 需要灵活决策、多轮迭代 → 考虑 Agent

### 3. 工具设计原则

工具是 Agent 与外部世界交互的桥梁，设计质量直接影响 Agent 效果。

**Tool 设计规范**:
```yaml
tool_name: get_weather
description: |
  获取指定城市的当前天气信息。
  返回温度、湿度、天气状况等。
  注意：只支持中国城市，使用中文城市名。
parameters:
  city:
    type: string
    description: 中文城市名，如"北京"、"上海"
    required: true
  unit:
    type: string
    enum: ["celsius", "fahrenheit"]
    default: "celsius"
examples:
  - input: { city: "北京" }
    output: { temp: 25, humidity: 60, condition: "晴" }
```

**最佳实践**:
- 名称清晰、动词开头（get_xxx, create_xxx, search_xxx）
- 描述详尽、包含使用场景和限制
- 参数有明确的类型、默认值、示例
- 错误处理友好、返回结构化错误信息

---

## Agent 架构模式

### 模式 1: Prompt Chaining（提示词链）

```
[Input] → [LLM Step 1] → [Gate/Check] → [LLM Step 2] → [Output]
```

**特点**: 固定流程，每步有明确职责，中间可插入校验

**适用场景**: 文档生成、内容审核、数据处理流水线

### 模式 2: Routing（路由分发）

```
           ┌→ [Agent A: 技术问题]
[Input] → [Router] → [Agent B: 业务问题]
           └→ [Agent C: 通用问答]
```

**特点**: 一个调度器根据输入类型分发到专门处理器

**适用场景**: 客服系统、多领域问答

### 模式 3: Parallelization（并行处理）

```
         ┌→ [LLM: 视角A] ─┐
[Input] →├→ [LLM: 视角B] ─┼→ [Aggregator] → [Output]
         └→ [LLM: 视角C] ─┘
```

**特点**: 同一任务从多角度并行处理，最后聚合结果

**适用场景**: 投票机制、多轮校验、观点综合

### 模式 4: Orchestrator-Workers（编排者-执行者）

```
[Input] → [Orchestrator] ──┬→ [Worker 1] ──┐
              ↑            ├→ [Worker 2] ──┼→ [Orchestrator] → [Output]
              └────────────└→ [Worker 3] ──┘
```

**特点**: 中央编排者动态分配任务，收集结果后决定下一步

**适用场景**: 复杂项目管理、代码重构、研究分析

### 模式 5: Evaluator-Optimizer（评估-优化循环）

```
         ┌──────────────────────────────┐
         ↓                              │
[Generator] → [Output] → [Evaluator] → [Optimizer] → [Improved Prompt]
                              ↓
                         [Pass?] → [Final Output]
```

**特点**: 自动评估输出质量，循环优化直到达标

**适用场景**: Agent 自我优化、Prompt 自动调优、测试驱动开发

**AgentEvo 采用此模式**

---

## Prompt 工程最佳实践

### 1. 结构化 Prompt 模板

```markdown
# Role（角色定义）
你是一个专业的 [领域] 助手...

# Context（上下文）
当前任务背景：...

# Instructions（指令）
请按以下步骤执行：
1. ...
2. ...

# Constraints（约束）
- 必须：...
- 禁止：...

# Output Format（输出格式）
请以 JSON 格式返回：
{
  "field1": "...",
  "field2": "..."
}

# Examples（示例）
输入：...
输出：...
```

### 2. 常见 Prompt 优化技巧

| 技巧 | 说明 | 示例 |
|------|------|------|
| Few-shot | 提供示例引导 | "例如：输入X → 输出Y" |
| Chain-of-Thought | 要求分步思考 | "请一步步分析" |
| Self-Consistency | 多次生成取共识 | 生成 5 次，取多数结果 |
| Role Playing | 角色扮演提升专业性 | "你是一位资深架构师" |
| Constraint Injection | 明确边界限制 | "只使用已提供的数据" |

### 3. Prompt 版本管理

```yaml
# prompt_versions/v1.0.0.md
version: 1.0.0
date: 2024-01-15
changes: 初始版本
metrics:
  accuracy: 0.75
  latency: 2.3s

# prompt_versions/v1.1.0.md
version: 1.1.0
date: 2024-01-20
changes: 增加 few-shot 示例
metrics:
  accuracy: 0.82  # +7%
  latency: 2.5s
```

---

## 评测框架设计（参考 promptfoo）

### 1. 核心概念

```yaml
# 测试配置结构
providers:        # LLM 提供者（可对比多个模型）
  - openai:gpt-4
  - anthropic:claude-3

prompts:          # 待测试的 Prompt 变体
  - prompts/v1.md
  - prompts/v2.md

tests:            # 测试用例集
  - description: "基础功能测试"
    vars:
      input: "..."
    assert:
      - type: contains
        value: "expected"
```

### 2. 评测指标类型

| 类型 | 说明 | 示例 |
|------|------|------|
| Exact Match | 精确匹配 | `output == expected` |
| Contains | 包含检查 | `"关键词" in output` |
| Regex | 正则匹配 | `r"\d{4}-\d{2}-\d{2}"` |
| JSON Schema | 结构验证 | 输出符合指定 schema |
| LLM-as-Judge | AI 评判 | 让另一个 LLM 打分 |
| Custom Function | 自定义函数 | Python 函数返回 bool |
| Semantic Similarity | 语义相似度 | embedding 余弦相似度 |

### 3. LLM-as-Judge 模板

```markdown
# Judge Prompt

你是一个专业的评测专家。请评估以下 AI 回答的质量。

## 评测维度
1. 准确性 (0-10): 答案是否正确
2. 完整性 (0-10): 是否覆盖所有要点
3. 清晰度 (0-10): 表达是否清晰易懂

## 待评测内容
**问题**: {{question}}
**标准答案**: {{expected}}
**AI回答**: {{output}}

## 输出格式
{
  "accuracy": <分数>,
  "completeness": <分数>,
  "clarity": <分数>,
  "pass": <true/false>,
  "reason": "<评判理由>"
}
```

### 4. 测试用例设计原则

- **覆盖边界**: 正常、异常、边界条件
- **多样性**: 不同输入类型、长度、复杂度
- **回归保护**: 已修复的 bug 要有对应测试
- **可复现**: 固定 seed，确保结果稳定

---

## 错误诊断与归因

### 1. 错误分类

```python
ERROR_CATEGORIES = {
    "hallucination": "幻觉/编造事实",
    "instruction_violation": "违反指令约束",
    "format_error": "输出格式错误",
    "incomplete": "回答不完整",
    "irrelevant": "答非所问",
    "reasoning_error": "推理逻辑错误",
    "tool_misuse": "工具使用错误",
    "context_miss": "上下文遗漏",
}
```

### 2. 归因分析模板

```markdown
# Diagnosis Prompt

分析以下测试失败的根本原因：

## 失败信息
- 测试描述: {{test_description}}
- 输入: {{input}}
- 期望: {{expected}}
- 实际: {{actual}}
- 断言失败: {{assertion_error}}

## 当前 Prompt
{{current_prompt}}

## 分析要求
1. 确定错误类别（从预定义类别中选择）
2. 定位 Prompt 中导致问题的具体部分
3. 分析根本原因
4. 提出修复建议

## 输出格式
{
  "error_category": "...",
  "root_cause": "...",
  "problematic_section": "...",
  "fix_suggestion": "..."
}
```

---

## 自动优化策略

### 1. 优化方向

| 优化类型 | 触发条件 | 优化动作 |
|----------|----------|----------|
| 添加约束 | 输出违反规则 | 在 Constraints 部分增加明确限制 |
| 增加示例 | 格式/风格不对 | 添加 Few-shot 示例 |
| 澄清指令 | 理解偏差 | 重写模糊的指令部分 |
| 拆分步骤 | 复杂任务失败 | 将指令拆解为更细的步骤 |
| 增强上下文 | 信息不足 | 补充必要的背景信息 |

### 2. 优化 Prompt 模板

```markdown
# Optimizer Prompt

基于错误诊断结果，优化以下 Prompt：

## 当前 Prompt
{{current_prompt}}

## 诊断结果
{{diagnosis}}

## 优化原则
1. 最小改动：只修改必要部分
2. 保持兼容：不破坏已通过的测试
3. 可验证：改动后应能解决诊断的问题

## 输出
返回完整的优化后 Prompt（不是 diff）
```

### 3. 回归测试

优化后必须：
1. 重跑失败的测试 → 验证修复
2. 重跑全部测试 → 确保无回归

---

## 竞品分析总结

### 1. promptfoo

**定位**: 开源 LLM 评测 CLI 工具

**核心功能**:
- YAML 配置驱动的测试
- 多 Provider 对比
- 丰富的断言类型
- 红队测试（安全性）
- Web UI 可视化

**优势**: 易用、灵活、社区活跃

**不足**: 缺少自动优化闭环

### 2. LangSmith

**定位**: LangChain 生态的可观测性平台

**核心功能**:
- Trace 追踪
- 数据集管理
- 在线评测
- Prompt Playground

**优势**: 与 LangChain 深度集成

**不足**: 闭源、依赖 LangChain 生态

### 3. Anthropic Evals

**定位**: Anthropic 内部评测框架

**核心功能**:
- 标准化测试集
- 多维度评估
- 安全性测试

**设计理念**:
- 重视安全性
- 强调可解释性
- 推崇简单架构

### 4. AgentEvo 差异化定位

```
promptfoo  →  评测为主，无自动优化
LangSmith  →  可观测性为主，闭源
AgentEvo   →  评测 + 诊断 + 自动优化 完整闭环
```

---

## 项目配置参考

### agent-evo.yaml 完整示例

```yaml
# AgentEvo 配置文件
name: my-agent
version: 1.0.0

# Agent 入口配置
agent:
  type: callable
  module: agent
  function: run

# 系统 Prompt 路径
prompt_file: system_prompt.md

# LLM 配置
llm:
  provider: openai
  model: gpt-4
  temperature: 0.7

# 测试配置
tests_dir: tests/

# 评测配置
evaluation:
  judge_model: gpt-4
  pass_threshold: 0.8
  max_retries: 3

# 优化配置
optimization:
  enabled: true
  max_iterations: 5
  strategy: minimal_change

# Git 集成
git:
  auto_branch: true
  branch_prefix: agent-evo/optimize
  pr_enabled: true
```

---

## 快速参考卡片

### Agent 开发检查清单

- [ ] 任务是否真的需要 Agent？（能否用简单 Prompt 解决）
- [ ] 选择了合适的架构模式？
- [ ] Prompt 结构清晰、包含示例？
- [ ] 工具定义完整、描述准确？
- [ ] 有完善的测试用例？
- [ ] 有监控和日志？
- [ ] 有错误处理机制？
- [ ] 考虑了安全性？

### Prompt 优化检查清单

- [ ] 角色定义清晰？
- [ ] 指令具体明确？
- [ ] 有输出格式要求？
- [ ] 有约束和边界？
- [ ] 有 Few-shot 示例？
- [ ] 版本化管理？

---

## 参考资源

- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [promptfoo Documentation](https://promptfoo.dev/docs/intro)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [OpenAI Best Practices](https://platform.openai.com/docs/guides/prompt-engineering)
