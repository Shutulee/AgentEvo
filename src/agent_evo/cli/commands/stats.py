"""stats 命令：查看测评集统计
stats command: view test suite statistics"""

from typing import Optional
from collections import Counter
from glob import glob
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from agent_evo.core.config import load_config
from agent_evo.models.test_case import TestCase, TestSuite
from agent_evo.utils.i18n import t

console = Console()


def _load_cases_only(config) -> list[TestCase]:
    """只加载测试用例，不初始化 Agent（stats 不需要执行 Agent）
    Load test cases only, no Agent initialization (stats doesn't need Agent execution)"""
    pattern = str(Path.cwd() / config.test_cases)
    files = glob(pattern, recursive=True)

    cases = []
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "cases" not in data:
            continue
        suite = TestSuite(**data)
        for case_data in suite.cases:
            if isinstance(case_data, dict):
                case = TestCase(**case_data)
            else:
                case = case_data
            cases.append(case)
    return cases


def run_stats(config_path: str):
    """按 tier/tag 统计用例数量分布 / Show test case statistics by tier/tag"""
    try:
        config = load_config(config_path)
        cases = _load_cases_only(config)

        console.print(f"\n[bold]{t('stats_title')}[/bold] ({t('stats_total').format(n=len(cases))})\n")

        # 按 tier 统计 / Statistics by tier
        tier_counter = Counter(c.tier.value for c in cases)
        table = Table(title=t("by_tier"), show_header=True, header_style="bold")
        table.add_column(t("tier"))
        table.add_column(t("count"), justify="right")
        for tier, count in tier_counter.most_common():
            table.add_row(tier, str(count))
        console.print(table)

        # 按 tag 统计 / Statistics by tag
        tag_counter: Counter = Counter()
        for c in cases:
            tag_counter.update(c.tags)

        if tag_counter:
            console.print()
            table2 = Table(title=t("by_tag"), show_header=True, header_style="bold")
            table2.add_column(t("tag"))
            table2.add_column(t("count"), justify="right")
            for tag, count in tag_counter.most_common():
                table2.add_row(tag, str(count))
            console.print(table2)

        # 按 source 统计 / Statistics by source
        source_counter = Counter(c.source.value for c in cases)
        console.print()
        table3 = Table(title=t("by_source"), show_header=True, header_style="bold")
        table3.add_column(t("source"))
        table3.add_column(t("count"), justify="right")
        for src, count in source_counter.most_common():
            table3.add_row(src, str(count))
        console.print(table3)

        # 按审核状态统计 / Statistics by review status
        review_counter = Counter(c.review_status.value for c in cases)
        pending = review_counter.get("pending", 0)
        if pending > 0:
            console.print(f"\n[yellow]{t('pending_review').format(n=pending)}[/yellow]")

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
