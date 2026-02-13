"""report 命令 / report command"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console

from agent_evo.utils.i18n import t

console = Console()


def show_report(
    input_file: str,
    format: str,
    output: Optional[str]
):
    """显示或转换报告 / Display or convert report"""
    input_path = Path(input_file)

    if not input_path.exists():
        console.print(f"[red]❌ {t('config_file_missing').format(path=input_file)}[/red]")
        raise SystemExit(1)

    # 读取报告 / Read report
    report_data = json.loads(input_path.read_text(encoding="utf-8"))

    if format == "terminal":
        _print_terminal_report(report_data)
    elif format == "json":
        if output:
            Path(output).write_text(
                json.dumps(report_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            console.print(f"✅ JSON {t('report_saved').format(path=output)}")
        else:
            console.print(json.dumps(report_data, indent=2, ensure_ascii=False))
    elif format == "html":
        html_content = _generate_html_report(report_data)
        if output:
            Path(output).write_text(html_content, encoding="utf-8")
            console.print(f"✅ HTML {t('report_saved').format(path=output)}")
        else:
            console.print(html_content)
    else:
        console.print(f"[red]❌ {t('unsupported_format').format(fmt=format)}[/red]")
        raise SystemExit(1)


def _print_terminal_report(data: dict):
    """在终端打印报告 / Print report in terminal"""
    from rich.table import Table

    console.print(f"\n[bold]{t('eval_report_title')}[/bold]\n")

    # 概览 / Overview
    pass_rate = data.get("pass_rate", 0)
    status_color = "green" if pass_rate >= 0.95 else "red" if pass_rate < 0.7 else "yellow"

    console.print(f"{t('pass_rate')}: [{status_color}]{pass_rate:.1%}[/{status_color}]")
    console.print(f"{t('total')}: {data.get('total', 0)}  {t('passed')}: {data.get('passed', 0)}  {t('failed')}: {data.get('failed', 0)}")

    # 详细结果 / Detailed results
    results = data.get("results", [])
    if results:
        console.print(f"\n[bold]{t('detailed_results')}[/bold]\n")

        table = Table()
        table.add_column(t("col_id"))
        table.add_column(t("col_status"))
        table.add_column(t("col_score"))
        table.add_column(t("col_summary"))

        for r in results:
            status = r.get("status", "unknown")
            status_display = {
                "passed": "[green]✅[/green]",
                "failed": "[red]❌[/red]",
                "error": "[yellow]⚠[/yellow]"
            }.get(status, status)

            table.add_row(
                r.get("case_id", ""),
                status_display,
                f"{r.get('score', 0):.2f}",
                r.get("summary", "")[:50]
            )

        console.print(table)


def _generate_html_report(data: dict) -> str:
    """生成 HTML 报告 / Generate HTML report"""
    from agent_evo.utils.i18n import get_language
    lang = get_language()

    pass_rate = data.get("pass_rate", 0)
    status_class = "success" if pass_rate >= 0.95 else "danger" if pass_rate < 0.7 else "warning"

    results_html = ""
    for r in data.get("results", []):
        status = r.get("status", "unknown")
        passed_label = t("passed") if lang == "zh" else "Passed"
        failed_label = t("failed") if lang == "zh" else "Failed"
        error_label = t("error") if lang == "zh" else "Error"
        status_badge = {
            "passed": f'<span class="badge bg-success">{passed_label}</span>',
            "failed": f'<span class="badge bg-danger">{failed_label}</span>',
            "error": f'<span class="badge bg-warning">{error_label}</span>'
        }.get(status, status)

        results_html += f"""
        <tr>
            <td>{r.get("case_id", "")}</td>
            <td>{r.get("case_name", "")}</td>
            <td>{status_badge}</td>
            <td>{r.get("score", 0):.2f}</td>
            <td>{r.get("summary", "")}</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{t('html_title')}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container py-4">
        <h1>🧬 {t('html_title')}</h1>

        <div class="card my-4">
            <div class="card-body">
                <h5 class="card-title">{t('html_overview')}</h5>
                <p class="display-4 text-{status_class}">{pass_rate:.1%}</p>
                <p>{t('total')}: {data.get("total", 0)} | {t('passed')}: {data.get("passed", 0)} | {t('failed')}: {data.get("failed", 0)}</p>
            </div>
        </div>

        <h3>{t('html_detailed')}</h3>
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>{t('col_id')}</th>
                    <th>{t('col_name')}</th>
                    <th>{t('col_status')}</th>
                    <th>{t('col_score')}</th>
                    <th>{t('col_summary')}</th>
                </tr>
            </thead>
            <tbody>
                {results_html}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
