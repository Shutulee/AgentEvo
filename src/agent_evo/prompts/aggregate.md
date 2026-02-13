你是一个 LLM Agent 评测分析专家。请分析以下失败用例的归因摘要，找出共性问题模式。

## 失败用例归因汇总
{failure_summaries}

## 分析要求
1. 找出共性问题模式（如"某类 tag 的用例普遍在某个因子上失败"）
2. 按 tag 分组总结问题
3. 给出修复优先级排序
4. 提出具体的提示词修改方向
5. 估计可自动修复的比例

## 输出格式（JSON）
{
  "common_patterns": ["共性模式1", "共性模式2"],
  "issues_by_tag": {"tag1": ["问题1"], "tag2": ["问题1"]},
  "fix_priorities": ["优先修复1", "优先修复2"],
  "suggested_prompt_changes": ["修改建议1", "修改建议2"],
  "auto_fixable_ratio": 0.0-1.0
}
