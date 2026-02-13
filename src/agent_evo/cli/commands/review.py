"""review 命令：审核待审核用例"""

from pathlib import Path
from glob import glob

import yaml
from rich.console import Console
from rich.table import Table

from agent_evo.core.config import load_config
from agent_evo.core.serializer import load_test_cases_from_yaml, save_test_cases

console = Console()


def run_review(config_path: str, status: str, approve_all: bool, interactive: bool):
    """查看/审核待审核用例"""
    try:
        config = load_config(config_path)

        # 扫描所有测试文件
        test_pattern = config.test_cases
        files = sorted(glob(test_pattern))
        if not files:
            console.print("[yellow]未找到测试文件[/yellow]")
            return

        pending_cases = []
        case_file_map = {}  # case_id -> file_path

        for f in files:
            cases = load_test_cases_from_yaml(f)
            for c in cases:
                if c.review_status.value == status:
                    pending_cases.append(c)
                    case_file_map[c.id] = f

        if not pending_cases:
            console.print(f"[green]没有 {status} 状态的用例[/green]")
            return

        console.print(f"找到 {len(pending_cases)} 条 {status} 状态的用例\n")

        if approve_all:
            # 全部通过
            _batch_update_status(files, status, "approved")
            console.print(f"[green]已将 {len(pending_cases)} 条用例全部标记为 approved[/green]")
            return

        # 展示列表
        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="cyan")
        table.add_column("名称")
        table.add_column("来源")
        table.add_column("变异方式", max_width=30)
        table.add_column("输入", max_width=40)

        for c in pending_cases:
            table.add_row(
                c.id, c.name, c.source.value,
                c.mutation_strategy or "-",
                c.input_query[:40] + "..." if len(c.input_query) > 40 else c.input_query,
            )
        console.print(table)

        if interactive:
            console.print("\n[bold]交互式审核（a=通过, r=拒绝, s=跳过）[/bold]\n")
            updates = {}
            for c in pending_cases:
                console.print(f"[cyan]{c.id}[/cyan]: {c.name}")
                console.print(f"  输入: {c.input_query}")
                console.print(f"  期望: {c.expected.model_dump(exclude_none=True)}")
                if c.mutation_strategy:
                    console.print(f"  变异: {c.mutation_strategy}")

                choice = input("  [a/r/s] > ").strip().lower()
                if choice == "a":
                    updates[c.id] = "approved"
                elif choice == "r":
                    updates[c.id] = "rejected"
                console.print()

            if updates:
                _update_cases_status(files, updates)
                approved = sum(1 for v in updates.values() if v == "approved")
                rejected = sum(1 for v in updates.values() if v == "rejected")
                console.print(f"[green]通过 {approved} 条, 拒绝 {rejected} 条[/green]")

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)


def _batch_update_status(files: list[str], from_status: str, to_status: str):
    """批量更新用例状态"""
    for f in files:
        path = Path(f)
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        if not data or "cases" not in data:
            continue

        changed = False
        for case in data["cases"]:
            if case.get("review_status", "approved") == from_status:
                case["review_status"] = to_status
                changed = True

        if changed:
            with open(path, "w", encoding="utf-8") as fh:
                yaml.dump(data, fh, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _update_cases_status(files: list[str], updates: dict[str, str]):
    """更新指定用例的状态"""
    for f in files:
        path = Path(f)
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        if not data or "cases" not in data:
            continue

        changed = False
        for case in data["cases"]:
            if case.get("id") in updates:
                case["review_status"] = updates[case["id"]]
                changed = True

        if changed:
            with open(path, "w", encoding="utf-8") as fh:
                yaml.dump(data, fh, allow_unicode=True, default_flow_style=False, sort_keys=False)
