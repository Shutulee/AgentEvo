"""run 命令 / run command"""

from typing import Optional

from rich.console import Console

from agent_evo.core.config import load_config
from agent_evo.core.pipeline import Pipeline
from agent_evo.utils.i18n import t

console = Console()


async def run_pipeline(
    config_path: str,
    tags: Optional[list[str]],
    auto_fix: bool,
    create_pr: bool,
    dry_run: bool,
    tier: Optional[str] = None,
):
    """运行完整流程 / Run full pipeline"""
    try:
        config = load_config(config_path)
        pipeline = Pipeline(config)

        result = await pipeline.run(
            auto_fix=auto_fix,
            create_pr=create_pr,
            tags=tags,
            tier=tier,
            dry_run=dry_run,
        )

        console.print("\n" + "=" * 50)
        if result.success:
            console.print(f"[bold green]{t('pipeline_success')}[/bold green]")
        else:
            console.print(f"[bold red]{t('pipeline_done_with_failures')}[/bold red]")

        if result.pr_url:
            console.print(f"\nPR: {result.pr_url}")

        console.print()

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]{t('exec_failed').format(msg=e)}[/red]")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
