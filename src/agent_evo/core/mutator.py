"""变异扩充引擎"""

import json
import uuid
from pathlib import Path
from typing import Optional

from agent_evo.models import Config, TestCase
from agent_evo.models.test_case import TestCaseSource, TestCaseTier, ReviewStatus
from agent_evo.utils.llm import LLMClient


class Mutator:
    """测评集变异扩充引擎：基于种子用例，LLM 自由发挥生成变异"""

    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config.llm)
        self.mutate_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompt_dir / "mutate.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        return """你是一个测试用例变异专家。基于给定的种子测试用例，生成多个有意义的变异用例。

## 种子用例
{seed_case}

## 参考变异方向（仅供参考，你可以自由探索更好的变异方式）
{hint_directions}

## 要求
1. 每个变异用例都应该测试不同的场景或边界条件
2. 为每个变异用例提供一个理想回答（expected_output）
3. 变异要有实际测试价值，不要只做同义改写
4. 生成 {count} 个变异用例

## 输出格式（JSON）
{{
  "mutations": [
    {{
      "input": "变异后的用户输入",
      "name": "变异用例名称",
      "mutation_strategy": "你选择的变异方式（简短描述）",
      "expected_output": "理想的 Agent 回答",
      "tags": ["继承种子的tag", "新增的tag"]
    }}
  ]
}}"""

    async def mutate(
        self,
        seed_cases: list[TestCase],
        count_per_case: int = 3,
        business_docs: Optional[str] = None,
    ) -> list[TestCase]:
        """批量变异生成测试用例"""
        all_mutations: list[TestCase] = []

        for seed in seed_cases:
            mutations = await self._mutate_single(seed, count_per_case, business_docs)
            all_mutations.extend(mutations)

        return all_mutations

    async def _mutate_single(
        self,
        seed: TestCase,
        count: int,
        business_docs: Optional[str] = None,
    ) -> list[TestCase]:
        """对单条种子用例变异"""
        # 构建种子信息
        seed_info = {
            "id": seed.id,
            "name": seed.name,
            "input": seed.input_query,
            "tags": seed.tags,
        }
        # 优先展示 expected_output，其次展示精确校验规则
        if seed.expected_output:
            seed_info["expected_output"] = seed.expected_output
        else:
            seed_info["expected"] = seed.expected.model_dump(exclude_none=True)

        # 参考方向
        hints = self.config.mutation.hint_directions
        hint_str = "\n".join(f"- {h}" for h in hints) if hints else "无特定方向，请自由发挥"

        prompt = self.mutate_prompt.format(
            seed_case=json.dumps(seed_info, ensure_ascii=False, indent=2),
            hint_directions=hint_str,
            count=count,
        )

        if business_docs:
            prompt += f"\n\n## 业务文档（参考）\n{business_docs}"

        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.8,
            )
            data = json.loads(response)
            mutations = data.get("mutations", [])

            result = []
            for i, m in enumerate(mutations):
                case_id = f"{seed.id}-mut-{uuid.uuid4().hex[:6]}"
                case = TestCase(
                    id=case_id,
                    name=m.get("name", f"{seed.name} 变异{i+1}"),
                    input=m.get("input", ""),
                    expected_output=m.get("expected_output"),
                    expected=m.get("expected", {}),
                    tags=m.get("tags", seed.tags),
                    source=TestCaseSource.MUTATION,
                    parent_id=seed.id,
                    mutation_strategy=m.get("mutation_strategy"),
                    review_status=ReviewStatus.PENDING,
                    tier=TestCaseTier.SILVER,
                )
                result.append(case)
            return result

        except Exception as e:
            return []

    async def review_batch(self, cases: list[TestCase]) -> list[TestCase]:
        """LLM 预审：检查变异用例的逻辑合理性，标记可疑项"""
        if not cases:
            return cases

        cases_info = []
        for c in cases:
            cases_info.append({
                "id": c.id,
                "input": c.input_query,
                "expected_output": c.expected_output or "",
                "mutation_strategy": c.mutation_strategy,
            })

        prompt = f"""你是一个测试用例审核专家。请检查以下变异生成的测试用例是否合理。

## 待审核用例
{json.dumps(cases_info, ensure_ascii=False, indent=2)}

## 审核标准
1. 用例输入是否清晰、有意义
2. expected_output 是否与 input 逻辑一致
3. 是否有测试价值（不是简单重复）

## 输出格式（JSON）
{{
  "reviews": [
    {{"id": "用例ID", "approved": true/false, "reason": "审核理由"}}
  ]
}}"""

        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            data = json.loads(response)
            reviews = {r["id"]: r for r in data.get("reviews", [])}

            for case in cases:
                review = reviews.get(case.id)
                if review and not review.get("approved", True):
                    case.review_status = ReviewStatus.REJECTED
                    # 保留 reason 到 judge_hints 字段（复用）
                    case.judge_hints = f"[预审拒绝] {review.get('reason', '')}"

        except Exception:
            pass  # 预审失败不影响流程

        return cases
