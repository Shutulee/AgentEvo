"""评测因子引擎 / Evaluation factor engine

评测分为两类因子：
Evaluation is divided into two types of factors:
1. CoreJudgeFactor — 一次 LLM 调用，同时从内容准确性、行为正确性、结构完整性三个维度评判。
   One LLM call evaluating content accuracy, behavioral correctness, and structural completeness.
   LLM 会自动判断每个维度是否适用（如纯知识问答不涉及结构化），不适用的维度不参与加权。
   LLM auto-determines applicability per dimension; inapplicable dimensions are excluded from weighting.
   如果用户还额外提供了精确校验规则（关键词、JSON Schema 等），则在 LLM 评判之外叠加确定性检查。
   If user provides additional precise validation rules (keywords, JSON Schema, etc.), deterministic checks are layered on top.
2. CustomFactor — 用户提供自定义校验函数时才激活。
   Activated only when user provides custom validation functions.
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
from agent_evo.utils.i18n import t


class EvaluationFactor(ABC):
    """评测因子基类 / Evaluation factor base class"""

    factor_id: str = ""
    weight: float = 1.0
    fatal: bool = False

    @abstractmethod
    def is_triggered(self, expected: ExpectedOutput) -> bool:
        """根据 expected 字段判断是否激活 / Determine activation based on expected fields"""

    @abstractmethod
    async def evaluate(self, case: TestCase, output: str, llm: Optional[LLMClient] = None) -> list[FactorResult]:
        """执行评测，返回因子结果列表 / Execute evaluation, return factor result list"""


# ─── 核心评判因子（一次 LLM 调用，三个维度）─────────────────
# ─── Core judge factor (one LLM call, three dimensions) ──────

class CoreJudgeFactor(EvaluationFactor):
    """核心评判因子：一次 LLM 调用同时评判 content / behavior / structure 三个维度。
    Core judge factor: one LLM call evaluating content/behavior/structure dimensions.

    LLM 会自动判断每个维度是否适用（applicable），不适用的维度不参与评分。
    LLM auto-determines applicability; inapplicable dimensions are excluded from scoring.
    如果用户额外提供了精确校验规则，则在 LLM 评判之外叠加确定性检查。
    If user provides additional precise validation rules, deterministic checks are layered on top.
    """

    factor_id = "core"

    def __init__(self):
        self.judge_prompt = self._load_judge_prompt()
        # 三个子维度的权重和 fatal 配置，由 Evaluator 注入
        # Weight and fatal config for three sub-dimensions, injected by Evaluator
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

        # ── 1. LLM 一次性评判三个维度 / 1. LLM evaluates three dimensions at once ──
        llm_scores = {}
        if llm and case.expected.output:
            llm_scores = await self._llm_judge(case, output, llm)

        # ── 2. 叠加精确校验规则 / 2. Layer on precise validation rules ──
        extra_checks = self._run_extra_checks(case, output)

        # ── 3. 合并每个维度的分数 / 3. Merge scores for each dimension ──
        for dim_id in ["content", "behavior", "structure"]:
            llm_result = llm_scores.get(dim_id)
            dim_extras = extra_checks.get(dim_id, [])

            # 如果 LLM 标记为不适用，且没有额外校验规则，跳过该维度
            # If LLM marks as inapplicable and no extra checks, skip this dimension
            if llm_result and not llm_result.get("applicable", True) and not dim_extras:
                continue

            scores: list[tuple[str, float, str]] = []

            # LLM 评判结果 / LLM judge result
            if llm_result and llm_result.get("applicable", True):
                scores.append((f"llm_{dim_id}", llm_result.get("score", 0.0), llm_result.get("reason", "")))

            # 叠加的精确校验 / Layered precise checks
            scores.extend(dim_extras)

            if not scores:
                continue

            final_score = min(s for _, s, _ in scores)
            failed = [(n, r) for n, s, r in scores if s < 1.0 and r]
            reason = "; ".join(f"{n}: {r}" for n, r in failed) if failed else t("dim_pass").format(dim=dim_id)

            results.append(FactorResult(
                factor_id=dim_id,
                score=final_score,
                reason=reason,
                details={"checks": [{"source": n, "score": s, "reason": r} for n, s, r in scores]},
            ))

        return results

    async def _llm_judge(self, case: TestCase, output: str, llm: LLMClient) -> dict[str, dict]:
        """一次 LLM 调用，返回三个维度的评判结果
        One LLM call, return judge results for three dimensions"""
        judge_hints = case.judge_hints or ""
        hints_section = f"## 额外评判提示 / Additional judge hints\n{judge_hints}" if judge_hints else ""

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
            # Ensure return is dict[str, dict] format
            return {
                k: v for k, v in result.items()
                if isinstance(v, dict) and k in ("content", "behavior", "structure")
            }
        except Exception as e:
            # LLM 调用失败，所有维度返回错误
            # LLM call failed, return error for all dimensions
            return {
                dim: {"applicable": True, "score": 0.0, "reason": t("llm_judge_error").format(err=e)}
                for dim in ("content", "behavior", "structure")
            }

    def _run_extra_checks(self, case: TestCase, output: str) -> dict[str, list[tuple[str, float, str]]]:
        """运行用户额外提供的精确校验规则，按维度归类
        Run user-provided precise validation rules, grouped by dimension"""
        expected = case.expected
        checks: dict[str, list[tuple[str, float, str]]] = {}

        # ── content 维度的额外校验 / content dimension extra checks ──
        content_checks: list[tuple[str, float, str]] = []

        if expected.contains:
            found = [kw for kw in expected.contains if kw in output]
            score = len(found) / len(expected.contains)
            missing = [kw for kw in expected.contains if kw not in output]
            reason = t("missing_keywords").format(kw=missing) if missing else ""
            content_checks.append(("contains", score, reason))

        if expected.not_contains:
            violations = [kw for kw in expected.not_contains if kw in output]
            score = 0.0 if violations else 1.0
            reason = t("forbidden_keywords").format(kw=violations) if violations else ""
            content_checks.append(("not_contains", score, reason))

        if content_checks:
            checks["content"] = content_checks

        # ── structure 维度的额外校验 / structure dimension extra checks ──
        structure_checks: list[tuple[str, float, str]] = []
        parsed_output = self._try_parse_json(output)

        if expected.json_schema and parsed_output is not None:
            ok, reason = self._check_json_schema(parsed_output, expected.json_schema)
            structure_checks.append(("json_schema", 1.0 if ok else 0.0, reason))

        if expected.exact_json is not None:
            if parsed_output is None:
                structure_checks.append(("exact_json", 0.0, t("output_not_json")))
            else:
                ok = parsed_output == expected.exact_json
                structure_checks.append(("exact_json", 1.0 if ok else 0.0, "" if ok else t("json_mismatch")))

        if expected.json_path_assertions and parsed_output is not None:
            for assertion in expected.json_path_assertions:
                ok, reason = self._check_jsonpath(parsed_output, assertion)
                structure_checks.append((f"jsonpath:{assertion.path}", 1.0 if ok else 0.0, reason))

        if structure_checks:
            checks["structure"] = structure_checks

        return checks

    # ── 工具方法 / Utility methods ──

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
            return True, t("jsonschema_skip")
        except jsonschema.ValidationError as e:
            return False, str(e.message)

    @staticmethod
    def _check_jsonpath(data: Any, assertion) -> tuple[bool, str]:
        try:
            from jsonpath_ng import parse
        except ImportError:
            return True, t("jsonpath_skip")

        expr = parse(assertion.path)
        matches = [m.value for m in expr.find(data)]

        if assertion.operator == "exists":
            return (len(matches) > 0, "" if matches else t("path_not_exist").format(path=assertion.path))

        if not matches:
            return False, t("path_no_value").format(path=assertion.path)

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
            return False, t("unsupported_operator").format(op=op)

        return ok, "" if ok else t("expect_actual").format(op=op, expected=expected_val, actual=actual)


# ─── Custom 因子（自定义校验）/ Custom factor (custom validation) ──

class CustomFactor(EvaluationFactor):
    """自定义校验：动态导入用户提供的校验函数
    Custom validation: dynamically import user-provided validation functions"""

    factor_id = "custom"

    def is_triggered(self, expected: ExpectedOutput) -> bool:
        return expected.validator is not None

    async def evaluate(self, case: TestCase, output: str, llm: Optional[LLMClient] = None) -> list[FactorResult]:
        validator_path = case.expected.validator
        if not validator_path:
            return [FactorResult(factor_id=self.factor_id, score=1.0, reason=t("no_custom_check"))]

        try:
            module_path, func_name = validator_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)

            result = func(case.input_query, output, case.expected.model_dump())
            if isinstance(result, bool):
                return [FactorResult(
                    factor_id=self.factor_id,
                    score=1.0 if result else 0.0,
                    reason="" if result else t("custom_check_fail")
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
            return [FactorResult(factor_id=self.factor_id, score=0.0, reason=t("custom_check_error").format(err=e))]
