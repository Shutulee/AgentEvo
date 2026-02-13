"""gate-check 命令：发布前门禁检查"""

from rich.console import Console

from agent_evo.core.config import load_config
from agent_evo.core.pipeline import Pipeline

console = Console()


async def run_gate_check(config_path: str):
    """运行所有 required_for_release 的 tag，任一不达标则退出码非零"""
    try:
        config = load_config(config_path)
        pipeline = Pipeline(config)

        # 找出所有 required_for_release 的 tag
        required_tags = [
            tag for tag, policy in config.tag_policies.items()
            if policy.required_for_release
        ]

        if not required_tags:
            console.print("[yellow]未配置任何 required_for_release 的 tag_policies，门禁检查跳过[/yellow]")
            return

        console.print(f"[bold]门禁检查: 检查 {', '.join(required_tags)} 标签[/bold]\n")

        report = await pipeline.eval_only(tags=required_tags)

        # 检查每个 tag 是否达标
        all_passed = True
        for tag in required_tags:
            stats = report.stats_by_tag.get(tag)
            policy = config.tag_policies[tag]
            if stats:
                status = "[green]PASS[/green]" if stats.meets_threshold else "[red]FAIL[/red]"
                console.print(f"  {tag}: {status} (通过率 {stats.pass_rate:.1%}, 阈值 {policy.pass_threshold:.1%})")
                if not stats.meets_threshold:
                    all_passed = False
            else:
                console.print(f"  {tag}: [dim]无用例[/dim]")

        if all_passed:
            console.print("\n[bold green]门禁检查通过[/bold green]")
        else:
            console.print("\n[bold red]门禁检查失败，阻断发布[/bold red]")
            raise SystemExit(1)

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
