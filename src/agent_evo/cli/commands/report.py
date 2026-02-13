"""report 命令"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def show_report(
    input_file: str,
    format: str,
    output: Optional[str]
):
    """显示或转换报告"""
    input_path = Path(input_file)
    
    if not input_path.exists():
        console.print(f"[red]❌ 报告文件不存在: {input_file}[/red]")
        raise SystemExit(1)
    
    # 读取报告
    report_data = json.loads(input_path.read_text(encoding="utf-8"))
    
    if format == "terminal":
        _print_terminal_report(report_data)
    elif format == "json":
        if output:
            Path(output).write_text(
                json.dumps(report_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            console.print(f"✅ JSON 报告已保存: {output}")
        else:
            console.print(json.dumps(report_data, indent=2, ensure_ascii=False))
    elif format == "html":
        html_content = _generate_html_report(report_data)
        if output:
            Path(output).write_text(html_content, encoding="utf-8")
            console.print(f"✅ HTML 报告已保存: {output}")
        else:
            console.print(html_content)
    else:
        console.print(f"[red]❌ 不支持的格式: {format}[/red]")
        raise SystemExit(1)


def _print_terminal_report(data: dict):
    """在终端打印报告"""
    from rich.table import Table
    
    console.print("\n[bold]📊 AgentEvo 评测报告[/bold]\n")
    
    # 概览
    pass_rate = data.get("pass_rate", 0)
    status_color = "green" if pass_rate >= 0.95 else "red" if pass_rate < 0.7 else "yellow"
    
    console.print(f"通过率: [{status_color}]{pass_rate:.1%}[/{status_color}]")
    console.print(f"总计: {data.get('total', 0)}  通过: {data.get('passed', 0)}  失败: {data.get('failed', 0)}")
    
    # 详细结果
    results = data.get("results", [])
    if results:
        console.print("\n[bold]详细结果:[/bold]\n")
        
        table = Table()
        table.add_column("ID")
        table.add_column("状态")
        table.add_column("评分")
        table.add_column("摘要")
        
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
    """生成 HTML 报告"""
    pass_rate = data.get("pass_rate", 0)
    status_class = "success" if pass_rate >= 0.95 else "danger" if pass_rate < 0.7 else "warning"
    
    results_html = ""
    for r in data.get("results", []):
        status = r.get("status", "unknown")
        status_badge = {
            "passed": '<span class="badge bg-success">通过</span>',
            "failed": '<span class="badge bg-danger">失败</span>',
            "error": '<span class="badge bg-warning">错误</span>'
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
    <title>AgentEvo 评测报告</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container py-4">
        <h1>🧬 AgentEvo 评测报告</h1>
        
        <div class="card my-4">
            <div class="card-body">
                <h5 class="card-title">概览</h5>
                <p class="display-4 text-{status_class}">{pass_rate:.1%}</p>
                <p>总计: {data.get("total", 0)} | 通过: {data.get("passed", 0)} | 失败: {data.get("failed", 0)}</p>
            </div>
        </div>
        
        <h3>详细结果</h3>
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>名称</th>
                    <th>状态</th>
                    <th>评分</th>
                    <th>摘要</th>
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
