"""gate-check 命令：发布前门禁检查
gate-check command: pre-release gate check"""

from rich.console import Console

from agent_evo.core.config import load_config
from agent_evo.core.pipeline import Pipeline
from agent_evo.utils.i18n import t

console = Console()


async def run_gate_check(config_path: str):
    """运行所有 required_for_release 的 tag，任一不达标则退出码非零
    Run all required_for_release tags, exit non-zero if any fails"""
    try:
        config = load_config(config_path)
        pipeline = Pipeline(config)

        # 找出所有 required_for_release 的 tag
        # Find all required_for_release tags
        required_tags = [
            tag for tag, policy in config.tag_policies.items()
            if policy.required_for_release
        ]

        if not required_tags:
            console.print(f"[yellow]{t('gate_check_skip')}[/yellow]")
            return

        console.print(f"[bold]{t('gate_check_title').format(tags=', '.join(required_tags))}[/bold]\n")

        report = await pipeline.eval_only(tags=required_tags)

        # 检查每个 tag 是否达标 / Check if each tag meets threshold
        all_passed = True
        for tag in required_tags:
            stats = report.stats_by_tag.get(tag)
            policy = config.tag_policies[tag]
            if stats:
                status = "[green]PASS[/green]" if stats.meets_threshold else "[red]FAIL[/red]"
                console.print(f"  {tag}: {status} ({t('pass_rate')} {stats.pass_rate:.1%}, threshold {policy.pass_threshold:.1%})")
                if not stats.meets_threshold:
                    all_passed = False
            else:
                console.print(f"  {tag}: [dim]{t('gate_no_cases')}[/dim]")

        if all_passed:
            console.print(f"\n[bold green]{t('gate_check_pass')}[/bold green]")
        else:
            console.print(f"\n[bold red]{t('gate_check_fail')}[/bold red]")
            raise SystemExit(1)

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
