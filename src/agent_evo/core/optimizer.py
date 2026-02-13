"""提示词优化器 / Prompt optimizer"""

import re
from pathlib import Path
from typing import Optional, Union

from agent_evo.models import Config, TestCase, OptimizationResult, AggregatedDiagnosis
from agent_evo.utils.llm import LLMClient


class Optimizer:
    """提示词优化器 / Prompt optimizer"""

    def __init__(self, config: Config, project_dir: Path):
        self.config = config
        self.project_dir = project_dir
        self.llm = LLMClient(config.llm)
        self.optimize_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompt_dir / "optimize.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return """你是一个 Prompt 工程专家。请根据诊断结果优化系统提示词。
You are a Prompt engineering expert. Optimize the system prompt based on diagnosis results.

## 当前提示词 / Current Prompt
{current_prompt}

## 诊断结果 / Diagnosis
{diagnoses}

## 要求 / Requirements
1. 保守修改，只修复必要部分 / Conservative changes, fix only necessary parts
2. 保持原有风格和结构 / Keep original style and structure
3. 避免过拟合单个用例 / Avoid overfitting to single cases

请直接输出优化后的完整提示词，用 <optimized_prompt> 和 </optimized_prompt> 标签包裹。
Output the optimized prompt wrapped in <optimized_prompt> and </optimized_prompt> tags."""

    async def optimize(
        self,
        test_cases: list[TestCase],
        aggregated_diagnosis: Optional[AggregatedDiagnosis] = None,
    ) -> OptimizationResult:
        """根据聚合归因结果优化提示词 / Optimize prompt based on aggregated diagnosis"""
        prompt_file = self.project_dir / self.config.agent.prompt_file

        if not prompt_file.exists():
            return OptimizationResult(success=False, error_message=f"Prompt file not found: {prompt_file}")

        original_prompt = prompt_file.read_text(encoding="utf-8")
        current_prompt = original_prompt

        # 构建诊断信息 / Build diagnosis info
        diagnoses_str = self._build_diagnoses_str(aggregated_diagnosis)

        for iteration in range(self.config.optimization.max_iterations):
            prompt = self.optimize_prompt.format(
                current_prompt=current_prompt,
                diagnoses=diagnoses_str,
            )

            try:
                response = await self.llm.chat(messages=[{"role": "user", "content": prompt}])
                new_prompt = self._extract_optimized_prompt(response)

                if not new_prompt:
                    return OptimizationResult(
                        success=False, iterations=iteration + 1,
                        error_message="Cannot extract optimized prompt from LLM response",
                    )

                # 写入文件 / Write to file
                prompt_file.write_text(new_prompt, encoding="utf-8")

                # 回归测试 / Regression test
                if self.config.optimization.run_regression:
                    from agent_evo.core.generator import Generator
                    from agent_evo.core.evaluator import Evaluator

                    generator = Generator(self.config, self.project_dir)
                    evaluator = Evaluator(self.config)
                    generator.adapter = generator._create_adapter()

                    results = await generator.run_all(test_cases)
                    report = await evaluator.evaluate_all(results)

                    if report.pass_rate >= self.config.optimization.regression_threshold:
                        return OptimizationResult(
                            success=True, iterations=iteration + 1,
                            original_prompt=original_prompt, optimized_prompt=new_prompt,
                            regression_pass_rate=report.pass_rate,
                        )
                    current_prompt = new_prompt
                else:
                    return OptimizationResult(
                        success=True, iterations=iteration + 1,
                        original_prompt=original_prompt, optimized_prompt=new_prompt,
                    )
            except Exception as e:
                prompt_file.write_text(original_prompt, encoding="utf-8")
                return OptimizationResult(success=False, iterations=iteration + 1, error_message=str(e))

        # 达到最大迭代次数，恢复原始提示词
        # Max iterations reached, restore original prompt
        prompt_file.write_text(original_prompt, encoding="utf-8")
        return OptimizationResult(
            success=False, iterations=self.config.optimization.max_iterations,
            original_prompt=original_prompt, optimized_prompt=current_prompt,
            error_message="Max iterations reached, original prompt restored",
        )

    @staticmethod
    def _build_diagnoses_str(
        aggregated: Optional[AggregatedDiagnosis],
    ) -> str:
        """构建诊断信息字符串 / Build diagnosis info string"""
        parts = []

        if aggregated:
            if aggregated.common_patterns:
                parts.append("Common patterns:\n" + "\n".join(f"- {p}" for p in aggregated.common_patterns))
            if aggregated.fix_priorities:
                parts.append("Fix priorities:\n" + "\n".join(f"- {p}" for p in aggregated.fix_priorities))
            if aggregated.suggested_prompt_changes:
                parts.append("Suggested changes:\n" + "\n".join(f"- {s}" for s in aggregated.suggested_prompt_changes))

        return "\n\n".join(parts) if parts else "No specific diagnosis information"

    def _extract_optimized_prompt(self, response: str) -> Optional[str]:
        match = re.search(r'<optimized_prompt>(.*?)</optimized_prompt>', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        lines = response.strip().split('\n')
        start_markers = ['#', '你是', '你好', 'You are', 'As a']
        for i, line in enumerate(lines):
            if any(line.strip().startswith(m) for m in start_markers):
                return '\n'.join(lines[i:]).strip()
        return None
