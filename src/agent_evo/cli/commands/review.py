"""review 命令：审核待审核用例
review command: review pending test cases"""

from pathlib import Path
from glob import glob

import yaml
from rich.console import Console
from rich.table import Table

from agent_evo.core.config import load_config
from agent_evo.core.serializer import load_test_cases_from_yaml, save_test_cases
from agent_evo.utils.i18n import t

console = Console()


def run_review(config_path: str, status: str, approve_all: bool, interactive: bool):
    """查看/审核待审核用例 / View/review pending test cases"""
    try:
        config = load_config(config_path)

        # 扫描所有测试文件 / Scan all test files
        test_pattern = config.test_cases
        files = sorted(glob(test_pattern))
        if not files:
            console.print(f"[yellow]{t('no_test_files')}[/yellow]")
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
            console.print(f"[green]{t('no_status_cases').format(status=status)}[/green]")
            return

        console.print(t("found_pending").format(n=len(pending_cases), status=status))
        console.print()

        if approve_all:
            # 全部通过 / Approve all
            _batch_update_status(files, status, "approved")
            console.print(f"[green]{t('batch_approved').format(n=len(pending_cases))}[/green]")
            return

        # 展示列表 / Display list
        table = Table(show_header=True, header_style="bold")
        table.add_column(t("col_id"), style="cyan")
        table.add_column(t("col_name"))
        table.add_column(t("source"))
        table.add_column(t("col_mutation_strategy"), max_width=30)
        table.add_column(t("col_input"), max_width=40)

        for c in pending_cases:
            table.add_row(
                c.id, c.name, c.source.value,
                c.mutation_strategy or "-",
                c.input_query[:40] + "..." if len(c.input_query) > 40 else c.input_query,
            )
        console.print(table)

        if interactive:
            console.print(f"\n[bold]{t('interactive_hint')}[/bold]\n")
            updates = {}
            for c in pending_cases:
                console.print(f"[cyan]{c.id}[/cyan]: {c.name}")
                console.print(f"  {t('col_input')}: {c.input_query}")
                console.print(f"  expected: {c.expected.model_dump(exclude_none=True)}")
                if c.mutation_strategy:
                    console.print(f"  mutation: {c.mutation_strategy}")

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
                console.print(f"[green]{t('review_result').format(a=approved, r=rejected)}[/green]")

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)


def _batch_update_status(files: list[str], from_status: str, to_status: str):
    """批量更新用例状态 / Batch update case status"""
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
    """更新指定用例的状态 / Update status for specified cases"""
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
