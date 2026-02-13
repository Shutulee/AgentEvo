"""eval 命令 / eval command"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from agent_evo.core.config import load_config
from agent_evo.core.pipeline import Pipeline
from agent_evo.utils.i18n import t

console = Console()


async def run_eval(
    config_path: str,
    tags: Optional[list[str]],
    output: Optional[str],
    tier: Optional[str] = None,
):
    """运行评测 / Run evaluation"""
    try:
        config = load_config(config_path)
        pipeline = Pipeline(config)
        report = await pipeline.eval_only(tags=tags, tier=tier)

        # 显示结果 / Display results
        _print_report(report)

        # 保存报告 / Save report
        if output:
            output_path = Path(output)
            output_path.write_text(
                report.model_dump_json(indent=2),
                encoding="utf-8"
            )
            console.print(f"\n{t('report_saved').format(path=output)}")

    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]{t('eval_failed').format(msg=e)}[/red]")
        raise SystemExit(1)


def _print_report(report):
    """打印评测报告 / Print evaluation report"""
    console.print(f"\n[bold]{t('eval_report_title')}[/bold]\n")

    # 概览 / Overview
    status_color = "green" if report.pass_rate >= 0.95 else "red" if report.pass_rate < 0.7 else "yellow"
    console.print(f"{t('pass_rate')}: [{status_color}]{report.pass_rate:.1%}[/{status_color}]")
    console.print(f"{t('total')}: {report.total}  {t('passed')}: {report.passed}  {t('failed')}: {report.failed}  {t('error')}: {report.error}")

    if report.duration_seconds:
        console.print(f"{t('duration')}: {report.duration_seconds:.2f}s")

    # 详细结果表格 / Detailed results table
    if report.results:
        console.print(f"\n[bold]{t('detailed_results')}[/bold]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column(t("col_id"), style="cyan")
        table.add_column(t("col_name"))
        table.add_column(t("col_status"))
        table.add_column(t("col_score"))
        table.add_column(t("col_summary"), max_width=40)

        for r in report.results:
            status_style = {
                "passed": f"[green]{t('status_passed')}[/green]",
                "failed": f"[red]{t('status_failed')}[/red]",
                "error": f"[yellow]{t('status_error')}[/yellow]",
                "skipped": f"[dim]{t('status_skipped')}[/dim]"
            }.get(r.status.value, r.status.value)

            table.add_row(
                r.case_id,
                r.case_name,
                status_style,
                f"{r.score:.2f}",
                r.summary[:40] + "..." if len(r.summary) > 40 else r.summary
            )

        console.print(table)
