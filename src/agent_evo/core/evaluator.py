"""因子化评测引擎 / Factor-based evaluation engine"""

from typing import Optional

from agent_evo.models import (
    Config, CaseResult, CaseStatus, EvalReport, TagStats,
    FactorResult, FactorSummary,
)
from agent_evo.models.config import FactorConfig
from agent_evo.core.generator import GeneratorResult
from agent_evo.core.factors import (
    EvaluationFactor, CoreJudgeFactor, CustomFactor,
)
from agent_evo.utils.llm import LLMClient
from agent_evo.utils.i18n import t


class Evaluator:
    """因子化评测引擎 / Factor-based evaluation engine

    核心逻辑 / Core logic:
    1. 根据 expected 字段自动激活对应因子 / Auto-activate factors based on expected fields
    2. 各因子独立评分（0-1 + reason）/ Each factor scores independently (0-1 + reason)
    3. 检查致命因子 → 加权汇总 → 判定通过/失败 / Check fatal factors → weighted sum → pass/fail
    """

    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config.llm)
        self.factors = self._init_factors()

    def _init_factors(self) -> list[EvaluationFactor]:
        """初始化因子列表，注入配置的权重和 fatal 设置
        Initialize factor list, inject configured weights and fatal settings"""
        factors: list[EvaluationFactor] = []

        # 核心评判因子（一次 LLM 调用，三个维度）
        # Core judge factor (one LLM call, three dimensions)
        core = CoreJudgeFactor()
        core.dimension_configs = {
            dim_id: {"weight": cfg.weight, "fatal": cfg.fatal}
            for dim_id, cfg in self.config.judge.factors.items()
            if dim_id in ("content", "behavior", "structure")
        }
        factors.append(core)

        # 自定义因子 / Custom factor
        custom = CustomFactor()
        custom_cfg: FactorConfig = self.config.judge.factors.get("custom", FactorConfig())
        custom.weight = custom_cfg.weight
        custom.fatal = custom_cfg.fatal
        factors.append(custom)

        return factors

    # ── 单条用例评测 / Single case evaluation ────────────────

    async def evaluate_case(self, result: GeneratorResult) -> CaseResult:
        """因子化评测单条用例 / Factor-based evaluation for a single case"""
        case = result.case

        # 执行出错，直接返回 / Execution error, return directly
        if result.error:
            return CaseResult(
                case_id=case.id, case_name=case.name, status=CaseStatus.ERROR,
                input=case.input_query, output=result.output,
                expected=case.expected.model_dump(), score=0.0,
                summary=t("exec_error").format(err=result.error),
                execution_time_ms=result.execution_time_ms,
                error_message=result.error, tags=case.tags,
            )

        # 1. 激活因子并收集所有维度结果
        # 1. Activate factors and collect all dimension results
        all_factor_results: list[FactorResult] = []
        for f in self.factors:
            if f.is_triggered(case.expected):
                results_list = await f.evaluate(case, result.output, llm=self.llm)
                all_factor_results.extend(results_list)

        # 无因子激活时，降级为简单通过
        # When no factor is activated, degrade to simple pass
        if not all_factor_results:
            return CaseResult(
                case_id=case.id, case_name=case.name, status=CaseStatus.PASSED,
                input=case.input_query, output=result.output,
                expected=case.expected.model_dump(), score=1.0, passed=True,
                weighted_score=1.0, summary=t("no_factor_activated"),
                execution_time_ms=result.execution_time_ms, tags=case.tags,
            )

        # 2. 获取每个维度的权重和 fatal 配置
        # 2. Get weight and fatal config for each dimension
        factor_configs = self._get_factor_configs()

        # 3. 致命因子检查 / 3. Fatal factor check
        for fr in all_factor_results:
            cfg = factor_configs.get(fr.factor_id, {})
            if cfg.get("fatal", False) and fr.score < 1.0:
                return CaseResult(
                    case_id=case.id, case_name=case.name, status=CaseStatus.FAILED,
                    input=case.input_query, output=result.output,
                    expected=case.expected.model_dump(),
                    factor_scores=all_factor_results, weighted_score=0.0,
                    score=0.0, passed=False,
                    fail_reason=t("fatal_factor_fail").format(fid=fr.factor_id, reason=fr.reason),
                    summary=t("fatal_factor_summary").format(fid=fr.factor_id),
                    execution_time_ms=result.execution_time_ms, tags=case.tags,
                )

        # 4. 加权汇总 / 4. Weighted aggregation
        total_weight = 0.0
        weighted_sum = 0.0
        for fr in all_factor_results:
            w = factor_configs.get(fr.factor_id, {}).get("weight", 1.0)
            total_weight += w
            weighted_sum += w * fr.score

        weighted_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        passed = weighted_score >= self.config.judge.pass_threshold

        fail_reason = None
        if not passed:
            failed_factors = [
                f"{fr.factor_id}({fr.score:.2f}): {fr.reason}"
                for fr in all_factor_results if fr.score < 1.0
            ]
            fail_reason = t("weighted_below_threshold").format(score=weighted_score, threshold=self.config.judge.pass_threshold) + "; " + "; ".join(failed_factors)

        return CaseResult(
            case_id=case.id, case_name=case.name,
            status=CaseStatus.PASSED if passed else CaseStatus.FAILED,
            input=case.input_query, output=result.output,
            expected=case.expected.model_dump(),
            factor_scores=all_factor_results, weighted_score=weighted_score,
            score=weighted_score, passed=passed, fail_reason=fail_reason,
            summary=t("weighted_score_summary").format(score=weighted_score),
            execution_time_ms=result.execution_time_ms, tags=case.tags,
        )

    def _get_factor_configs(self) -> dict[str, dict]:
        """从配置和 CoreJudgeFactor 中提取所有维度的权重/fatal
        Extract weight/fatal for all dimensions from config and CoreJudgeFactor"""
        configs: dict[str, dict] = {}
        for f in self.factors:
            if isinstance(f, CoreJudgeFactor):
                for dim_id, dim_cfg in f.dimension_configs.items():
                    configs[dim_id] = dim_cfg
            else:
                configs[f.factor_id] = {"weight": f.weight, "fatal": f.fatal}
        return configs

    # ── 批量评测 / Batch evaluation ──────────────────────────

    async def evaluate_all(self, results: list[GeneratorResult]) -> EvalReport:
        """批量评测所有用例，生成统一报告
        Batch evaluate all cases and generate unified report"""
        case_results = []
        for result in results:
            case_result = await self.evaluate_case(result)
            case_results.append(case_result)

        # 统计 / Statistics
        total = len(case_results)
        passed = sum(1 for r in case_results if r.status == CaseStatus.PASSED)
        failed = sum(1 for r in case_results if r.status == CaseStatus.FAILED)
        error = sum(1 for r in case_results if r.status == CaseStatus.ERROR)

        # 按 tag 统计 / Statistics by tag
        stats_by_tag: dict[str, TagStats] = {}
        failures_by_tag: dict[str, list[str]] = {}
        for r in case_results:
            for tag in r.tags:
                if tag not in stats_by_tag:
                    stats_by_tag[tag] = TagStats()
                stats = stats_by_tag[tag]
                stats.total += 1
                if r.status == CaseStatus.PASSED:
                    stats.passed += 1
                elif r.status == CaseStatus.FAILED:
                    stats.failed += 1
                    failures_by_tag.setdefault(tag, []).append(r.case_id)

        # 计算 tag 通过率 + 策略达标
        # Calculate tag pass rate + policy compliance
        release_blocked = False
        blocking_tags: list[str] = []
        for tag, stats in stats_by_tag.items():
            stats.pass_rate = stats.passed / stats.total if stats.total > 0 else 0.0
            policy = self.config.tag_policies.get(tag)
            if policy:
                stats.threshold = policy.pass_threshold
                stats.meets_threshold = stats.pass_rate >= policy.pass_threshold
                if policy.required_for_release and not stats.meets_threshold:
                    release_blocked = True
                    blocking_tags.append(tag)

        # 因子维度汇总 / Factor dimension summary
        factor_summary = self._compute_factor_summary(case_results)

        return EvalReport(
            total=total, passed=passed, failed=failed, error=error,
            pass_rate=passed / total if total > 0 else 0.0,
            results=case_results,
            stats_by_tag=stats_by_tag,
            factor_summary=factor_summary,
            release_blocked=release_blocked,
            blocking_tags=blocking_tags,
            failures_by_tag=failures_by_tag,
        )

    @staticmethod
    def _compute_factor_summary(results: list[CaseResult]) -> dict[str, FactorSummary]:
        """汇总各因子全局统计 / Summarize global statistics per factor"""
        summaries: dict[str, dict] = {}
        for r in results:
            for fr in r.factor_scores:
                if fr.factor_id not in summaries:
                    summaries[fr.factor_id] = {"scores": [], "fail": 0, "fatal_fail": 0}
                s = summaries[fr.factor_id]
                s["scores"].append(fr.score)
                if fr.score < 1.0:
                    s["fail"] += 1

        return {
            fid: FactorSummary(
                factor_id=fid,
                activated_count=len(data["scores"]),
                avg_score=sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0,
                fail_count=data["fail"],
                fatal_fail_count=data["fatal_fail"],
            )
            for fid, data in summaries.items()
        }
