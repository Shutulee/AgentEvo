"""stats 命令：查看测评集统计"""

from typing import Optional
from collections import Counter

from rich.console import Console
from rich.table import Table

from agent_evo.core.config import load_config
from agent_evo.core.generator import Generator

console = Console()


def run_stats(config_path: str):
    """按 tier/tag 统计用例数量分布"""
    try:
        config = load_config(config_path)
        from pathlib import Path
        generator = Generator(config, Path.cwd())
        cases = generator.load_test_cases()

        console.print(f"\n[bold]测评集统计[/bold] (共 {len(cases)} 条用例)\n")

        # 按 tier 统计
        tier_counter = Counter(c.tier.value for c in cases)
        table = Table(title="按层级", show_header=True, header_style="bold")
        table.add_column("层级")
        table.add_column("数量", justify="right")
        for tier, count in tier_counter.most_common():
            table.add_row(tier, str(count))
        console.print(table)

        # 按 tag 统计
        tag_counter: Counter = Counter()
        for c in cases:
            tag_counter.update(c.tags)

        if tag_counter:
            console.print()
            table2 = Table(title="按标签", show_header=True, header_style="bold")
            table2.add_column("标签")
            table2.add_column("数量", justify="right")
            for tag, count in tag_counter.most_common():
                table2.add_row(tag, str(count))
            console.print(table2)

        # 按 source 统计
        source_counter = Counter(c.source.value for c in cases)
        console.print()
        table3 = Table(title="按来源", show_header=True, header_style="bold")
        table3.add_column("来源")
        table3.add_column("数量", justify="right")
        for src, count in source_counter.most_common():
            table3.add_row(src, str(count))
        console.print(table3)

        # 按审核状态统计
        review_counter = Counter(c.review_status.value for c in cases)
        pending = review_counter.get("pending", 0)
        if pending > 0:
            console.print(f"\n[yellow]有 {pending} 条用例待审核[/yellow]")

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
