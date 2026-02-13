"""eval 命令"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from agent_evo.core.config import load_config
from agent_evo.core.pipeline import Pipeline

console = Console()


async def run_eval(
    config_path: str,
    tags: Optional[list[str]],
    output: Optional[str],
    tier: Optional[str] = None,
):
    """运行评测"""
    try:
        config = load_config(config_path)
        pipeline = Pipeline(config)
        report = await pipeline.eval_only(tags=tags, tier=tier)
        
        # 显示结果
        _print_report(report)
        
        # 保存报告
        if output:
            output_path = Path(output)
            output_path.write_text(
                report.model_dump_json(indent=2),
                encoding="utf-8"
            )
            console.print(f"\n📄 报告已保存: {output}")
            
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]❌ 评测失败: {e}[/red]")
        raise SystemExit(1)


def _print_report(report):
    """打印评测报告"""
    console.print("\n[bold]📊 评测报告[/bold]\n")
    
    # 概览
    status_color = "green" if report.pass_rate >= 0.95 else "red" if report.pass_rate < 0.7 else "yellow"
    console.print(f"通过率: [{status_color}]{report.pass_rate:.1%}[/{status_color}]")
    console.print(f"总计: {report.total}  通过: {report.passed}  失败: {report.failed}  错误: {report.error}")
    
    if report.duration_seconds:
        console.print(f"耗时: {report.duration_seconds:.2f}s")
    
    # 详细结果表格
    if report.results:
        console.print("\n[bold]详细结果:[/bold]\n")
        
        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="cyan")
        table.add_column("名称")
        table.add_column("状态")
        table.add_column("评分")
        table.add_column("摘要", max_width=40)
        
        for r in report.results:
            status_style = {
                "passed": "[green]✅ 通过[/green]",
                "failed": "[red]❌ 失败[/red]",
                "error": "[yellow]⚠ 错误[/yellow]",
                "skipped": "[dim]⏭ 跳过[/dim]"
            }.get(r.status.value, r.status.value)
            
            table.add_row(
                r.case_id,
                r.case_name,
                status_style,
                f"{r.score:.2f}",
                r.summary[:40] + "..." if len(r.summary) > 40 else r.summary
            )
        
        console.print(table)
