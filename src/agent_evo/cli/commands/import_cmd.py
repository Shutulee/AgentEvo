"""import 命令：从线上数据导入测评集
import command: import test cases from production data"""

from rich.console import Console

from agent_evo.core.config import load_config
from agent_evo.core.importer import TestCaseImporter
from agent_evo.core.serializer import load_test_cases_from_yaml, save_test_cases
from agent_evo.utils.i18n import t

console = Console()


async def run_import(
    config_path: str,
    file_path: str,
    format: str,
    output_path: str,
    auto_refine: bool,
):
    """从线上数据导入测评集 / Import test cases from production data"""
    try:
        config = load_config(config_path)
        importer = TestCaseImporter(config)

        console.print(t("importing").format(path=file_path, fmt=format))

        # 导入 / Import
        cases, result = await importer.import_from_file(
            file_path=file_path,
            format=format,
            auto_refine=auto_refine,
        )

        if result.errors:
            for err in result.errors:
                console.print(f"[yellow]{t('warn')}: {err}[/yellow]")

        if not cases:
            console.print(f"[red]{t('no_cases_imported')}[/red]")
            raise SystemExit(1)

        # 去重（与已有用例对比）/ Deduplicate (compare with existing cases)
        try:
            from pathlib import Path
            if Path(output_path).exists():
                existing = load_test_cases_from_yaml(output_path)
                before = len(cases)
                cases = await importer.deduplicate(cases, existing)
                removed = before - len(cases)
                if removed:
                    console.print(f"[yellow]{t('dedup_removed')}: {removed}[/yellow]")
                    result.duplicates_removed = removed
        except Exception:
            pass

        # 写入文件 / Write to file
        path = save_test_cases(
            cases, output_path,
            name="Production Import / 线上导入测评集",
            description=f"Imported from / 导入自 {file_path}",
        )

        console.print(f"\n[green]{t('import_done')}[/green]")
        console.print(f"  {t('total_records')}: {result.total_records}")
        console.print(f"  {t('imported_count')}: {len(cases)}")
        console.print(f"  {t('dedup_removed')}: {result.duplicates_removed}")
        console.print(f"  {t('pending_count')}: {len(cases)}")
        console.print(f"  {t('output_file')}: {path}")
        console.print(f"\n[yellow]{t('import_review_hint')}[/yellow]")

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
