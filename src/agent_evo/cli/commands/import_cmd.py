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

        await _post_import(importer, cases, result, output_path, source_desc=file_path)

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)


async def run_import_from_source(
    config_path: str,
    source_name: str,
    output_path: str,
    auto_refine: bool,
):
    """从 HTTP API 数据源拉取并导入 / Fetch from HTTP API source and import"""
    try:
        config = load_config(config_path)

        # 查找数据源配置 / Find source config by name
        source = None
        for s in config.import_sources:
            if s.name == source_name:
                source = s
                break

        if source is None:
            available = [s.name for s in config.import_sources] or ["(none)"]
            console.print(
                f"[red]{t('source_not_found').format(name=source_name)}[/red]\n"
                f"  {t('available_sources')}: {', '.join(available)}"
            )
            raise SystemExit(1)

        importer = TestCaseImporter(config)

        console.print(t("fetching_source").format(name=source_name, url=source.url))

        cases, result = await importer.import_from_source(
            source=source,
            auto_refine=auto_refine,
        )

        await _post_import(importer, cases, result, output_path, source_desc=f"{source_name} ({source.url})")

    except Exception as e:
        console.print(f"[red]{t('fetch_source_error').format(err=e)}[/red]")
        raise SystemExit(1)


async def _post_import(
    importer: TestCaseImporter,
    cases: list,
    result,
    output_path: str,
    source_desc: str,
):
    """导入后的公共处理：去重、写入、打印结果 / Post-import: dedup, save, print results"""
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
        description=f"Imported from / 导入自 {source_desc}",
    )

    console.print(f"\n[green]{t('import_done')}[/green]")
    console.print(f"  {t('total_records')}: {result.total_records}")
    console.print(f"  {t('imported_count')}: {len(cases)}")
    console.print(f"  {t('dedup_removed')}: {result.duplicates_removed}")
    console.print(f"  {t('pending_count')}: {len(cases)}")
    console.print(f"  {t('output_file')}: {path}")
    console.print(f"\n[yellow]{t('import_review_hint')}[/yellow]")
