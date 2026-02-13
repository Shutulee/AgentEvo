你是一个测试用例提炼专家。基于线上 Bad Case 数据，生成标准的测试用例。

## 线上数据
- 用户输入: {query}
- Agent 错误回复: {agent_response}
- 纠错信息: {corrected_response}
- 错误类型: {error_type}

## 任务
1. 分析 Agent 的回复"错在哪"
2. 生成一个理想的回答（expected_output），即 Agent 应该如何正确回复
3. 自动打标签（至少包含 regression）

## 输出格式（严格 JSON）
{{
  "name": "用例名称（简短描述测试意图）",
  "expected_output": "理想的 Agent 回答",
  "tags": ["regression", "其他标签"]
}}
