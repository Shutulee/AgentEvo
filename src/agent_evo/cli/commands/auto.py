"""auto 命令 — 一站式评测 + 自动优化 / auto command — one-stop evaluation + auto optimization"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from agent_evo.core.config import load_config
from agent_evo.core.pipeline import Pipeline
from agent_evo.utils.i18n import t

console = Console()


async def run_auto(
    config_path: str,
    tags: Optional[list[str]] = None,
    tier: Optional[str] = None,
    include_silver: bool = False,
    create_pr: bool = False,
    output: Optional[str] = None,
):
    """一站式评测 + 自动优化 / One-stop evaluation + auto optimization"""
    try:
        config = load_config(config_path)
        pipeline = Pipeline(config)

        console.print(f"\n[bold cyan]{t('auto_start')}[/bold cyan]\n")

        # 运行完整 Pipeline（auto_fix=True, dry_run=False）
        # Run full pipeline (auto_fix=True, dry_run=False)
        result = await pipeline.run(
            auto_fix=True,
            create_pr=create_pr,
            tags=tags,
            tier=tier,
            include_silver=include_silver,
            dry_run=False,
        )

        report = result.eval_report

        # 保存报告 / Save report
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_path = Path(output) if output else report_dir / f"auto_{timestamp}.json"
        html_path = report_dir / f"auto_{timestamp}.html"

        report_json = report.model_dump_json(indent=2)
        json_path.write_text(report_json, encoding="utf-8")
        console.print(f"\n📄 JSON {t('report_saved').format(path=str(json_path))}")

        from agent_evo.cli.commands.report import _generate_html_report
        report_data = json.loads(report_json)
        html_content = _generate_html_report(report_data)
        html_path.write_text(html_content, encoding="utf-8")
        console.print(f"🌐 HTML {t('report_saved').format(path=str(html_path))}")

        # 打印最终结果摘要 / Print final result summary
        console.print("\n" + "=" * 50)
        if result.success:
            console.print(f"[bold green]{t('auto_success')}[/bold green]")
        elif result.optimization and result.optimization.success:
            console.print(f"[bold green]{t('auto_optimized')}[/bold green]")
        elif report.failed > 0:
            console.print(f"[bold yellow]{t('auto_partial')}[/bold yellow]")
        else:
            console.print(f"[bold green]{t('pipeline_success')}[/bold green]")

        if result.pr_url:
            console.print(f"\nPR: {result.pr_url}")

        console.print()

    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]{t('exec_failed').format(msg=e)}[/red]")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
