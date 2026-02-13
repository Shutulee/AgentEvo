"""import 命令：从线上数据导入测评集"""

from rich.console import Console

from agent_evo.core.config import load_config
from agent_evo.core.importer import TestCaseImporter
from agent_evo.core.serializer import load_test_cases_from_yaml, save_test_cases

console = Console()


async def run_import(
    config_path: str,
    file_path: str,
    format: str,
    output_path: str,
    auto_refine: bool,
):
    """从线上数据导入测评集"""
    try:
        config = load_config(config_path)
        importer = TestCaseImporter(config)

        console.print(f"正在导入 [bold]{file_path}[/bold] (格式: {format})")

        # 导入
        cases, result = await importer.import_from_file(
            file_path=file_path,
            format=format,
            auto_refine=auto_refine,
        )

        if result.errors:
            for err in result.errors:
                console.print(f"[yellow]警告: {err}[/yellow]")

        if not cases:
            console.print("[red]未导入任何用例[/red]")
            raise SystemExit(1)

        # 去重（与已有用例对比）
        try:
            from pathlib import Path
            if Path(output_path).exists():
                existing = load_test_cases_from_yaml(output_path)
                before = len(cases)
                cases = await importer.deduplicate(cases, existing)
                removed = before - len(cases)
                if removed:
                    console.print(f"[yellow]去重移除 {removed} 条重复用例[/yellow]")
                    result.duplicates_removed = removed
        except Exception:
            pass

        # 写入文件
        path = save_test_cases(
            cases, output_path,
            name="线上导入测评集",
            description=f"从 {file_path} 导入",
        )

        console.print(f"\n[green]导入完成[/green]")
        console.print(f"  总记录数: {result.total_records}")
        console.print(f"  成功导入: {len(cases)}")
        console.print(f"  去重移除: {result.duplicates_removed}")
        console.print(f"  待审核:   {len(cases)}")
        console.print(f"  输出文件: {path}")
        console.print(f"\n[yellow]所有用例状态为 pending，请通过 agent-evo review 审核[/yellow]")

    except FileNotFoundError as e:
        console.print(f"[red]文件未找到: {e}[/red]")
        raise SystemExit(1)
