"""评测因子引擎

评测分为两类因子：
1. CoreJudgeFactor — 一次 LLM 调用，同时从内容准确性、行为正确性、结构完整性三个维度评判。
   LLM 会自动判断每个维度是否适用（如纯知识问答不涉及结构化），不适用的维度不参与加权。
   如果用户还额外提供了精确校验规则（关键词、JSON Schema 等），则在 LLM 评判之外叠加确定性检查。
2. CustomFactor — 用户提供自定义校验函数时才激活。
"""

import importlib
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from agent_evo.models.test_case import ExpectedOutput, TestCase
from agent_evo.models.eval_result import FactorResult
from agent_evo.utils.llm import LLMClient


class EvaluationFactor(ABC):
    """评测因子基类"""

    factor_id: str = ""
    weight: float = 1.0
    fatal: bool = False

    @abstractmethod
    def is_triggered(self, expected: ExpectedOutput) -> bool:
        """根据 expected 字段判断是否激活"""

    @abstractmethod
    async def evaluate(self, case: TestCase, output: str, llm: Optional[LLMClient] = None) -> list[FactorResult]:
        """执行评测，返回因子结果列表"""


# ─── 核心评判因子（一次 LLM 调用，三个维度）─────────────────

class CoreJudgeFactor(EvaluationFactor):
    """核心评判因子：一次 LLM 调用同时评判 content / behavior / structure 三个维度。

    LLM 会自动判断每个维度是否适用（applicable），不适用的维度不参与评分。
    如果用户额外提供了精确校验规则，则在 LLM 评判之外叠加确定性检查。
    """

    factor_id = "core"

    def __init__(self):
        self.judge_prompt = self._load_judge_prompt()
        # 三个子维度的权重和 fatal 配置，由 Evaluator 注入
        self.dimension_configs: dict[str, dict] = {
            "content": {"weight": 1.0, "fatal": False},
            "behavior": {"weight": 0.8, "fatal": False},
            "structure": {"weight": 0.5, "fatal": False},
        }

    @staticmethod
    def _load_judge_prompt() -> str:
        prompt_file = Path(__file__).parent.parent / "prompts" / "judge.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return ""

    def is_triggered(self, expected: ExpectedOutput) -> bool:
        return expected.output is not None

    async def evaluate(self, case: TestCase, output: str, llm: Optional[LLMClient] = None) -> list[FactorResult]:
        results: list[FactorResult] = []

        # ── 1. LLM 一次性评判三个维度 ──
        llm_scores = {}
        if llm and case.expected.output:
            llm_scores = await self._llm_judge(case, output, llm)

        # ── 2. 叠加精确校验规则 ──
        extra_checks = self._run_extra_checks(case, output)

        # ── 3. 合并每个维度的分数 ──
        for dim_id in ["content", "behavior", "structure"]:
            llm_result = llm_scores.get(dim_id)
            dim_extras = extra_checks.get(dim_id, [])

            # 如果 LLM 标记为不适用，且没有额外校验规则，跳过该维度
            if llm_result and not llm_result.get("applicable", True) and not dim_extras:
                continue

            scores: list[tuple[str, float, str]] = []

            # LLM 评判结果
            if llm_result and llm_result.get("applicable", True):
                scores.append((f"llm_{dim_id}", llm_result.get("score", 0.0), llm_result.get("reason", "")))

            # 叠加的精确校验
            scores.extend(dim_extras)

            if not scores:
                continue

            final_score = min(s for _, s, _ in scores)
            failed = [(n, r) for n, s, r in scores if s < 1.0 and r]
            reason = "; ".join(f"{n}: {r}" for n, r in failed) if failed else f"{dim_id} 达标"

            results.append(FactorResult(
                factor_id=dim_id,
                score=final_score,
                reason=reason,
                details={"checks": [{"source": n, "score": s, "reason": r} for n, s, r in scores]},
            ))

        return results

    async def _llm_judge(self, case: TestCase, output: str, llm: LLMClient) -> dict[str, dict]:
        """一次 LLM 调用，返回三个维度的评判结果"""
        judge_hints = case.judge_hints or ""
        hints_section = f"## 额外评判提示\n{judge_hints}" if judge_hints else ""

        prompt = self.judge_prompt.format(
            input=case.input_query,
            expected=case.expected.output,
            output=output,
            judge_hints=hints_section,
        )

        try:
            response = await llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            result = json.loads(response)
            # 确保返回的是 dict[str, dict] 格式
            return {
                k: v for k, v in result.items()
                if isinstance(v, dict) and k in ("content", "behavior", "structure")
            }
        except Exception as e:
            # LLM 调用失败，所有维度返回错误
            return {
                dim: {"applicable": True, "score": 0.0, "reason": f"LLM 评判出错: {e}"}
                for dim in ("content", "behavior", "structure")
            }

    def _run_extra_checks(self, case: TestCase, output: str) -> dict[str, list[tuple[str, float, str]]]:
        """运行用户额外提供的精确校验规则，按维度归类"""
        expected = case.expected
        checks: dict[str, list[tuple[str, float, str]]] = {}

        # ── content 维度的额外校验 ──
        content_checks: list[tuple[str, float, str]] = []

        if expected.contains:
            found = [kw for kw in expected.contains if kw in output]
            score = len(found) / len(expected.contains)
            missing = [kw for kw in expected.contains if kw not in output]
            reason = f"缺少关键词: {missing}" if missing else ""
            content_checks.append(("contains", score, reason))

        if expected.not_contains:
            violations = [kw for kw in expected.not_contains if kw in output]
            score = 0.0 if violations else 1.0
            reason = f"包含禁止词: {violations}" if violations else ""
            content_checks.append(("not_contains", score, reason))

        if content_checks:
            checks["content"] = content_checks

        # ── structure 维度的额外校验 ──
        structure_checks: list[tuple[str, float, str]] = []
        parsed_output = self._try_parse_json(output)

        if expected.json_schema and parsed_output is not None:
            ok, reason = self._check_json_schema(parsed_output, expected.json_schema)
            structure_checks.append(("json_schema", 1.0 if ok else 0.0, reason))

        if expected.exact_json is not None:
            if parsed_output is None:
                structure_checks.append(("exact_json", 0.0, "输出不是有效的 JSON"))
            else:
                ok = parsed_output == expected.exact_json
                structure_checks.append(("exact_json", 1.0 if ok else 0.0, "" if ok else "JSON 不完全匹配"))

        if expected.json_path_assertions and parsed_output is not None:
            for assertion in expected.json_path_assertions:
                ok, reason = self._check_jsonpath(parsed_output, assertion)
                structure_checks.append((f"jsonpath:{assertion.path}", 1.0 if ok else 0.0, reason))

        if structure_checks:
            checks["structure"] = structure_checks

        return checks

    # ── 工具方法 ──

    @staticmethod
    def _try_parse_json(output: str) -> Optional[Any]:
        try:
            return json.loads(output)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r"```(?:json)?\s*\n(.*?)\n```", output, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except (json.JSONDecodeError, TypeError):
                    pass
            return None

    @staticmethod
    def _check_json_schema(data: Any, schema: dict) -> tuple[bool, str]:
        try:
            import jsonschema
            jsonschema.validate(data, schema)
            return True, ""
        except ImportError:
            return True, "jsonschema 库未安装，跳过校验"
        except jsonschema.ValidationError as e:
            return False, str(e.message)

    @staticmethod
    def _check_jsonpath(data: Any, assertion) -> tuple[bool, str]:
        try:
            from jsonpath_ng import parse
        except ImportError:
            return True, "jsonpath-ng 库未安装，跳过校验"

        expr = parse(assertion.path)
        matches = [m.value for m in expr.find(data)]

        if assertion.operator == "exists":
            return (len(matches) > 0, "" if matches else f"路径 {assertion.path} 不存在")

        if not matches:
            return False, f"路径 {assertion.path} 未找到值"

        actual = matches[0]
        op = assertion.operator
        expected_val = assertion.value

        if op == "eq":
            ok = actual == expected_val
        elif op == "neq":
            ok = actual != expected_val
        elif op == "in":
            ok = actual in expected_val
        elif op == "contains":
            ok = expected_val in str(actual)
        elif op == "regex":
            ok = bool(re.search(str(expected_val), str(actual)))
        else:
            return False, f"不支持的算子: {op}"

        return ok, "" if ok else f"期望 {op} {expected_val}，实际为 {actual}"


# ─── Custom 因子（自定义校验）─────────────────────────────

class CustomFactor(EvaluationFactor):
    """自定义校验：动态导入用户提供的校验函数"""

    factor_id = "custom"

    def is_triggered(self, expected: ExpectedOutput) -> bool:
        return expected.validator is not None

    async def evaluate(self, case: TestCase, output: str, llm: Optional[LLMClient] = None) -> list[FactorResult]:
        validator_path = case.expected.validator
        if not validator_path:
            return [FactorResult(factor_id=self.factor_id, score=1.0, reason="无自定义校验")]

        try:
            module_path, func_name = validator_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)

            result = func(case.input_query, output, case.expected.model_dump())
            if isinstance(result, bool):
                return [FactorResult(
                    factor_id=self.factor_id,
                    score=1.0 if result else 0.0,
                    reason="" if result else "自定义校验未通过"
                )]
            elif isinstance(result, dict):
                return [FactorResult(
                    factor_id=self.factor_id,
                    score=result.get("score", 0.0),
                    reason=result.get("reason", ""),
                    details=result
                )]
            else:
                return [FactorResult(factor_id=self.factor_id, score=float(result), reason="")]
        except Exception as e:
            return [FactorResult(factor_id=self.factor_id, score=0.0, reason=f"自定义校验出错: {e}")]



