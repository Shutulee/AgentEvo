"""Pipeline 编排器"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from agent_evo.models import Config, EvalReport, OptimizationResult
from agent_evo.core.generator import Generator
from agent_evo.core.evaluator import Evaluator
from agent_evo.core.optimizer import Optimizer
from agent_evo.integrations.git import GitIntegration


console = Console()


class PipelineResult:
    """Pipeline 执行结果"""
    
    def __init__(
        self,
        eval_report: EvalReport,
        optimization: Optional[OptimizationResult] = None,
        pr_url: Optional[str] = None
    ):
        self.eval_report = eval_report
        self.optimization = optimization
        self.pr_url = pr_url
    
    @property
    def success(self) -> bool:
        """是否成功（通过率达标或优化成功）"""
        if self.optimization and self.optimization.success:
            return True
        return self.eval_report.pass_rate >= 0.95


class Pipeline:
    """AgentEvo 核心 Pipeline"""
    
    def __init__(self, config: Config, project_dir: Optional[str] = None):
        self.config = config
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        
        self.generator = Generator(config, self.project_dir)
        self.evaluator = Evaluator(config)
        self.optimizer = Optimizer(config, self.project_dir)
        self.git = GitIntegration(config.git, self.project_dir) if config.git.enabled else None
    
    async def run(
        self,
        auto_fix: bool = False,
        create_pr: bool = False,
        tags: Optional[list[str]] = None,
        dry_run: bool = False
    ) -> PipelineResult:
        """
        运行完整流程
        
        Args:
            auto_fix: 是否自动修复失败用例
            create_pr: 是否创建 PR
            tags: 只运行指定 tag 的用例
            dry_run: 预览模式，不实际修改文件
            
        Returns:
            PipelineResult
        """
        console.print("\n[bold blue]🚀 AgentEvo Pipeline 启动[/bold blue]\n")
        
        # 1. 加载测试用例
        test_cases = self.generator.load_test_cases(tags=tags)
        console.print(f"📋 加载了 {len(test_cases)} 个测试用例")
        
        # 2. 执行测试
        console.print("\n[bold]▶ 执行测试...[/bold]")
        started_at = datetime.now()
        results = await self.generator.run_all(test_cases)
        
        # 3. 评判
        console.print("\n[bold]▶ 评判结果...[/bold]")
        eval_report = await self.evaluator.evaluate_all(results)
        eval_report.started_at = started_at
        eval_report.finished_at = datetime.now()
        eval_report.duration_seconds = (eval_report.finished_at - started_at).total_seconds()
        
        self._print_eval_summary(eval_report)
        
        optimization_result = None
        pr_url = None
        
        # 4. 如果有失败且开启自动修复
        if auto_fix and eval_report.failed > 0:
            console.print("\n[bold]▶ 诊断失败用例...[/bold]")
            
            failed_results = eval_report.get_failed_results()
            diagnoses = await self.evaluator.diagnose_all(failed_results)
            
            # 筛选可修复的（高置信度）
            fixable = [
                d for d in diagnoses 
                if d.auto_fixable and d.confidence >= self.config.diagnosis.confidence_threshold
            ]
            
            if fixable:
                console.print(f"🔧 发现 {len(fixable)} 个可自动修复的问题")
                
                if dry_run:
                    console.print("\n[yellow]⚠ Dry-run 模式，不实际修改文件[/yellow]")
                    for d in fixable:
                        console.print(f"  - {d.case_id}: {d.category.value} ({d.confidence:.0%})")
                        console.print(f"    建议: {d.suggestion}")
                else:
                    console.print("\n[bold]▶ 优化提示词...[/bold]")
                    optimization_result = await self.optimizer.optimize(
                        diagnoses=fixable,
                        test_cases=test_cases
                    )
                    
                    if optimization_result.success:
                        console.print(f"[green]✅ 优化成功！迭代 {optimization_result.iterations} 次[/green]")
                        
                        # 5. 创建 PR
                        if create_pr and self.git:
                            console.print("\n[bold]▶ 创建 PR...[/bold]")
                            pr_url = await self.git.create_pr(
                                title=f"[AgentEvo] 自动优化: 修复 {len(fixable)} 个失败用例",
                                body=self._generate_pr_body(eval_report, optimization_result, fixable),
                                changes=[(self.config.agent.prompt_file, optimization_result.optimized_prompt)]
                            )
                            console.print(f"[green]✅ PR 已创建: {pr_url}[/green]")
                    else:
                        console.print(f"[red]❌ 优化未能完全解决问题[/red]")
            else:
                console.print("[yellow]⚠ 没有可自动修复的问题（置信度不足或归因类型不支持）[/yellow]")
        
        return PipelineResult(
            eval_report=eval_report,
            optimization=optimization_result,
            pr_url=pr_url
        )
    
    async def eval_only(self, tags: Optional[list[str]] = None) -> EvalReport:
        """只运行评测，不优化"""
        test_cases = self.generator.load_test_cases(tags=tags)
        results = await self.generator.run_all(test_cases)
        return await self.evaluator.evaluate_all(results)
    
    def _print_eval_summary(self, report: EvalReport) -> None:
        """打印评测摘要"""
        status_icon = "✅" if report.pass_rate >= 0.95 else "❌" if report.pass_rate < 0.7 else "⚠️"
        
        console.print(f"\n{status_icon} [bold]评测结果[/bold]")
        console.print(f"   总计: {report.total}  通过: {report.passed}  失败: {report.failed}  错误: {report.error}")
        console.print(f"   通过率: {report.pass_rate:.1%}")
        console.print(f"   耗时: {report.duration_seconds:.2f}s")
        
        if report.failed > 0:
            console.print("\n[bold red]失败用例:[/bold red]")
            for r in report.get_failed_results()[:5]:  # 最多显示 5 个
                console.print(f"   - {r.case_id}: {r.summary[:50]}...")
    
    def _generate_pr_body(self, report: EvalReport, opt_result: OptimizationResult, diagnoses) -> str:
        """生成 PR 描述"""
        body = f"""## AgentEvo 自动优化报告

### 📊 评测结果
- 总用例: {report.total}
- 通过: {report.passed}
- 失败: {report.failed}
- 原始通过率: {report.pass_rate:.1%}

### 🔧 修复内容
"""
        for d in diagnoses:
            body += f"- **{d.case_id}**: {d.category.value}\n"
            body += f"  - 原因: {d.root_cause}\n"
            body += f"  - 置信度: {d.confidence:.0%}\n"
        
        if opt_result.regression_pass_rate:
            body += f"\n### ✅ 回归测试\n通过率: {opt_result.regression_pass_rate:.1%}\n"
        
        body += "\n---\n*由 AgentEvo 自动生成*"
        return body
