"""Pipeline 编排器 — Phase A-B-C-D 四阶段批量流程
Pipeline orchestrator — Phase A-B-C-D four-stage batch workflow"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from agent_evo.models import (
    Config, EvalReport, OptimizationResult, AggregatedDiagnosis, TestCase,
)
from agent_evo.core.generator import Generator
from agent_evo.core.evaluator import Evaluator
from agent_evo.core.optimizer import Optimizer
from agent_evo.integrations.git import GitIntegration
from agent_evo.utils.llm import LLMClient
from agent_evo.utils.i18n import t


console = Console()


class PipelineResult:
    """Pipeline 执行结果 / Pipeline execution result"""

    def __init__(
        self,
        eval_report: EvalReport,
        optimization: Optional[OptimizationResult] = None,
        pr_url: Optional[str] = None,
    ):
        self.eval_report = eval_report
        self.optimization = optimization
        self.pr_url = pr_url

    @property
    def success(self) -> bool:
        if self.optimization and self.optimization.success:
            return True
        return self.eval_report.pass_rate >= 0.95


class Pipeline:
    """AgentEvo 核心 Pipeline — 四阶段批量流程
    AgentEvo core Pipeline — four-stage batch workflow"""

    def __init__(self, config: Config, project_dir: Optional[str] = None):
        self.config = config
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.generator = Generator(config, self.project_dir)
        self.evaluator = Evaluator(config)
        self.optimizer = Optimizer(config, self.project_dir)
        self.git = GitIntegration(config.git, self.project_dir) if config.git.enabled else None
        self.llm = LLMClient(config.llm)

    async def run(
        self,
        auto_fix: bool = False,
        create_pr: bool = False,
        tags: Optional[list[str]] = None,
        tier: Optional[str] = None,
        dry_run: bool = False,
    ) -> PipelineResult:
        """四阶段批量流程 / Four-stage batch workflow"""
        console.print(f"\n[bold blue]{t('pipeline_start')}[/bold blue]\n")

        # ── Phase A：批量执行 + 评测（因子化，归因即时完成）──
        # ── Phase A: Batch execution + evaluation (factor-based, attribution done in-place) ──
        test_cases = self.generator.load_test_cases(tags=tags)
        if tier:
            test_cases = [c for c in test_cases if c.tier.value == tier]
        console.print(t("loaded_cases").format(n=len(test_cases)))

        console.print(f"\n[bold]{t('phase_a')}[/bold]")
        started_at = datetime.now()
        results = await self.generator.run_all(test_cases)
        eval_report = await self.evaluator.evaluate_all(results)
        eval_report.started_at = started_at
        eval_report.finished_at = datetime.now()
        eval_report.duration_seconds = (eval_report.finished_at - started_at).total_seconds()

        self._print_eval_summary(eval_report)

        optimization_result = None
        pr_url = None

        if auto_fix and eval_report.failed > 0:
            # ── Phase B：聚合分析（轻量，只传归因摘要）──
            # ── Phase B: Aggregated analysis (lightweight, only pass attribution summary) ──
            console.print(f"\n[bold]{t('phase_b')}[/bold]")
            aggregated = await self._aggregate_diagnosis(eval_report)
            eval_report.aggregated_diagnosis = aggregated

            if aggregated.suggested_prompt_changes:
                console.print(f"  {t('found_patterns').format(n=len(aggregated.common_patterns))}")

                if dry_run:
                    console.print(f"\n[yellow]{t('dry_run_mode')}[/yellow]")
                    for p in aggregated.common_patterns:
                        console.print(f"  - {p}")
                    for s in aggregated.suggested_prompt_changes:
                        console.print(f"  建议/Suggestion: {s}")
                else:
                    # ── Phase C：统一优化 + 回归验证 ──
                    # ── Phase C: Unified optimization + regression ──
                    console.print(f"\n[bold]{t('phase_c')}[/bold]")
                    optimization_result = await self.optimizer.optimize(
                        aggregated_diagnosis=aggregated,
                        test_cases=test_cases,
                    )

                    if optimization_result.success:
                        console.print(f"[green]{t('optimize_success').format(n=optimization_result.iterations)}[/green]")
                    else:
                        console.print(f"[red]{t('optimize_fail').format(msg=optimization_result.error_message)}[/red]")

                    # ── Phase D：生成报告 + 创建 PR ──
                    # ── Phase D: Generate report + create PR ──
                    if create_pr and self.git and optimization_result.success:
                        console.print(f"\n[bold]{t('phase_d')}[/bold]")
                        pr_url = await self.git.create_pr(
                            title=f"[AgentEvo] Auto-optimize: fix {eval_report.failed} failed cases",
                            body=self._generate_pr_body(eval_report, optimization_result, aggregated),
                            changes=[(self.config.agent.prompt_file, optimization_result.optimized_prompt)],
                        )
                        console.print(f"[green]{t('pr_created').format(url=pr_url)}[/green]")
            else:
                console.print(f"[yellow]{t('no_auto_fix_patterns')}[/yellow]")

        eval_report.optimization = optimization_result
        return PipelineResult(eval_report=eval_report, optimization=optimization_result, pr_url=pr_url)

    async def eval_only(self, tags: Optional[list[str]] = None, tier: Optional[str] = None) -> EvalReport:
        """只运行评测，不优化 / Run evaluation only, no optimization"""
        test_cases = self.generator.load_test_cases(tags=tags)
        if tier:
            test_cases = [c for c in test_cases if c.tier.value == tier]
        results = await self.generator.run_all(test_cases)
        return await self.evaluator.evaluate_all(results)

    # ── Phase B 聚合分析 / Phase B Aggregated analysis ────────

    async def _aggregate_diagnosis(self, report: EvalReport) -> AggregatedDiagnosis:
        """收集失败用例的因子 reason，用一次 LLM 调用找共性模式
        Collect factor reasons from failed cases, find common patterns with one LLM call"""
        failed = report.get_failed_results()
        if not failed:
            return AggregatedDiagnosis()

        # 构建归因摘要（只传 ID + tags + 因子 reason，省 token）
        # Build attribution summary (only ID + tags + factor reason to save tokens)
        summaries = []
        for r in failed:
            factor_info = "; ".join(
                f"{fr.factor_id}({fr.score:.2f}): {fr.reason}" for fr in r.factor_scores if fr.score < 1.0
            )
            summaries.append(f"- {r.case_id} [tags: {','.join(r.tags)}] → {factor_info or r.fail_reason or 'unknown'}")

        failure_text = "\n".join(summaries)

        # 加载聚合 prompt / Load aggregate prompt
        prompt_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompt_dir / "aggregate.md"
        if prompt_file.exists():
            template = prompt_file.read_text(encoding="utf-8")
        else:
            template = "分析以下失败用例归因，找出共性模式并给出修复建议。\n\n{failure_summaries}\n\n以 JSON 格式输出。"

        prompt = template.format(failure_summaries=failure_text)

        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            data = json.loads(response)
            return AggregatedDiagnosis(**data)
        except Exception:
            # 降级：从因子 reason 直接汇总 / Fallback: summarize from factor reasons
            return AggregatedDiagnosis(
                common_patterns=[t("common_fail_count").format(n=len(failed))],
                suggested_prompt_changes=[t("suggest_manual_check")],
            )

    # ── 输出 / Output ────────────────────────────────────────

    def _print_eval_summary(self, report: EvalReport) -> None:
        status_icon = "[green]PASS[/green]" if report.pass_rate >= 0.95 else "[red]FAIL[/red]" if report.pass_rate < 0.7 else "[yellow]WARN[/yellow]"

        console.print(f"\n{status_icon} [bold]{t('eval_result')}[/bold]")
        console.print(f"  {t('total')}: {report.total}  {t('passed')}: {report.passed}  {t('failed')}: {report.failed}  {t('error')}: {report.error}")
        console.print(f"  {t('pass_rate')}: {report.pass_rate:.1%}  {t('duration')}: {report.duration_seconds:.2f}s")

        # 因子维度汇总 / Factor dimension summary
        if report.factor_summary:
            console.print(f"\n  [bold]{t('factor_summary_title')}[/bold]")
            for fid, fs in report.factor_summary.items():
                console.print(f"    {t('factor_line').format(fid=fid, activated=fs.activated_count, avg=fs.avg_score, fail=fs.fail_count)}")

        # 门禁检查 / Gate check
        if report.release_blocked:
            console.print(f"\n  [bold red]{t('release_blocked').format(tags=', '.join(report.blocking_tags))}[/bold red]")

        # 失败用例 / Failed cases
        if report.failed > 0:
            console.print(f"\n  [bold red]{t('failed_cases_title')}[/bold red]")
            for r in report.get_failed_results()[:5]:
                console.print(f"    - {r.case_id}: {r.fail_reason or r.summary[:60]}")

    def _generate_pr_body(self, report: EvalReport, opt_result: OptimizationResult, diagnosis: AggregatedDiagnosis) -> str:
        body = f"""## AgentEvo Auto-Optimization Report

### Evaluation Result
- Total cases: {report.total}
- Pass rate: {report.pass_rate:.1%} (passed {report.passed} / failed {report.failed})

### Common Patterns
"""
        for p in diagnosis.common_patterns:
            body += f"- {p}\n"

        body += "\n### Suggested Changes\n"
        for s in diagnosis.suggested_prompt_changes:
            body += f"- {s}\n"

        if opt_result.regression_pass_rate:
            body += f"\n### Regression Test\nPass rate: {opt_result.regression_pass_rate:.1%}\n"

        body += "\n---\n*Auto-generated by AgentEvo*"
        return body
