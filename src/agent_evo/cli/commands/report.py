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
    import html as html_mod
    from agent_evo.utils.i18n import get_language
    lang = get_language()
    is_zh = lang == "zh"

    pass_rate = data.get("pass_rate", 0)
    status_class = "success" if pass_rate >= 0.95 else "danger" if pass_rate < 0.7 else "warning"

    # 标签 / Labels
    L = {
        "title": "AgentEvo 评测报告" if is_zh else "AgentEvo Evaluation Report",
        "overview": "概览" if is_zh else "Overview",
        "total": "总计" if is_zh else "Total",
        "passed": "通过" if is_zh else "Passed",
        "failed": "失败" if is_zh else "Failed",
        "error": "错误" if is_zh else "Error",
        "detailed": "详细结果" if is_zh else "Detailed Results",
        "tag_stats": "标签统计" if is_zh else "Tag Statistics",
        "factor_summary": "评判维度汇总" if is_zh else "Factor Summary",
        "tag": "标签" if is_zh else "Tag",
        "pass_rate": "通过率" if is_zh else "Pass Rate",
        "threshold": "阈值" if is_zh else "Threshold",
        "meets": "达标" if is_zh else "Meets",
        "factor": "维度" if is_zh else "Factor",
        "activated": "激活次数" if is_zh else "Activated",
        "avg_score": "平均分" if is_zh else "Avg Score",
        "fail_count": "未满分次数" if is_zh else "Sub-perfect",
        "input": "输入" if is_zh else "Input",
        "actual_output": "实际输出" if is_zh else "Actual Output",
        "expected_output": "期望输出" if is_zh else "Expected Output",
        "factor_scores": "各维度评分" if is_zh else "Factor Scores",
        "reason": "评判理由" if is_zh else "Reason",
        "score": "评分" if is_zh else "Score",
        "time": "耗时" if is_zh else "Duration",
        "error_msg": "错误信息" if is_zh else "Error Message",
        "yes": "是" if is_zh else "Yes",
        "no": "否" if is_zh else "No",
        "na": "N/A" if is_zh else "N/A",
        "status": "状态" if is_zh else "Status",
        "name": "名称" if is_zh else "Name",
        "click_expand": "点击展开详情" if is_zh else "Click to expand",
    }

    def esc(text: str) -> str:
        return html_mod.escape(str(text)) if text else ""

    def nl2br(text: str) -> str:
        return esc(text).replace("\n", "<br>")

    # ── 结果卡片 ──
    results_html = ""
    for idx, r in enumerate(data.get("results", [])):
        status = r.get("status", "unknown")
        status_badge = {
            "passed": f'<span class="badge bg-success">{L["passed"]}</span>',
            "failed": f'<span class="badge bg-danger">{L["failed"]}</span>',
            "error": f'<span class="badge bg-warning text-dark">{L["error"]}</span>',
        }.get(status, status)

        tags_html = " ".join(
            f'<span class="badge bg-secondary me-1">{esc(tag)}</span>'
            for tag in r.get("tags", [])
        )

        exec_time = r.get("execution_time_ms")
        time_str = f"{exec_time / 1000:.1f}s" if exec_time else "-"

        # 各维度评分
        factors_html = ""
        for fs in r.get("factor_scores", []):
            bar_width = int(fs.get("score", 0) * 100)
            bar_color = "success" if fs["score"] >= 0.9 else "warning" if fs["score"] >= 0.7 else "danger"
            factors_html += f"""
            <div class="mb-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <strong>{esc(fs.get("factor_id", ""))}</strong>
                    <span class="badge bg-{bar_color}">{fs.get("score", 0):.2f}</span>
                </div>
                <div class="progress" style="height: 6px;">
                    <div class="progress-bar bg-{bar_color}" style="width: {bar_width}%"></div>
                </div>
                <small class="text-muted">{esc(fs.get("reason", ""))}</small>
            </div>
            """

        # 错误信息
        error_html = ""
        if r.get("error_message"):
            error_html = f"""
            <div class="alert alert-danger mt-2 mb-0">
                <strong>{L["error_msg"]}:</strong> {esc(r["error_message"])}
            </div>
            """

        # 期望输出
        expected_output = ""
        expected = r.get("expected", {})
        if expected and expected.get("output"):
            expected_output = expected["output"]

        results_html += f"""
        <div class="card mb-3 border-start border-4 border-{
            "success" if status == "passed" else "danger" if status == "failed" else "warning"
        }">
            <div class="card-header d-flex justify-content-between align-items-center"
                 style="cursor:pointer" data-bs-toggle="collapse" data-bs-target="#detail-{idx}">
                <div>
                    <strong>{esc(r.get("case_id", ""))}</strong>
                    <span class="text-muted ms-2">{esc(r.get("case_name", ""))}</span>
                    {tags_html}
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="text-muted">{time_str}</span>
                    <span class="fw-bold">{r.get("score", 0):.2f}</span>
                    {status_badge}
                    <i class="bi bi-chevron-down"></i>
                </div>
            </div>
            <div id="detail-{idx}" class="collapse">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6>{L["input"]}</h6>
                            <div class="bg-light p-2 rounded mb-3" style="white-space:pre-wrap;max-height:200px;overflow-y:auto;">{nl2br(r.get("input", "")) or '<em class="text-muted">(empty)</em>'}</div>

                            <h6>{L["actual_output"]}</h6>
                            <div class="bg-light p-2 rounded mb-3" style="white-space:pre-wrap;max-height:300px;overflow-y:auto;">{nl2br(r.get("output", "")) or '<em class="text-muted">(empty)</em>'}</div>

                            <h6>{L["expected_output"]}</h6>
                            <div class="bg-light p-2 rounded" style="white-space:pre-wrap;max-height:200px;overflow-y:auto;">{nl2br(expected_output) or '<em class="text-muted">-</em>'}</div>
                        </div>
                        <div class="col-md-6">
                            <h6>{L["factor_scores"]}</h6>
                            {factors_html if factors_html else '<p class="text-muted">-</p>'}
                            {error_html}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """

    # ── 标签统计 ──
    tag_stats_html = ""
    for tag, stats in data.get("stats_by_tag", {}).items():
        tag_pass_rate = stats.get("pass_rate", 0)
        tag_color = "success" if tag_pass_rate >= 0.95 else "warning" if tag_pass_rate >= 0.7 else "danger"
        threshold = stats.get("threshold")
        meets = stats.get("meets_threshold")
        meets_str = f'<span class="badge bg-{"success" if meets else "danger"}">{L["yes"] if meets else L["no"]}</span>' if meets is not None else L["na"]
        tag_stats_html += f"""
        <tr>
            <td><span class="badge bg-secondary">{esc(tag)}</span></td>
            <td>{stats.get("total", 0)}</td>
            <td>{stats.get("passed", 0)}</td>
            <td>{stats.get("failed", 0)}</td>
            <td class="text-{tag_color} fw-bold">{tag_pass_rate:.0%}</td>
            <td>{f"{threshold:.0%}" if threshold is not None else L["na"]}</td>
            <td>{meets_str}</td>
        </tr>
        """

    # ── 因子汇总 ──
    factor_summary_html = ""
    for fid, fs in data.get("factor_summary", {}).items():
        avg = fs.get("avg_score", 0)
        bar_color = "success" if avg >= 0.9 else "warning" if avg >= 0.7 else "danger"
        factor_summary_html += f"""
        <tr>
            <td><strong>{esc(fid)}</strong></td>
            <td>{fs.get("activated_count", 0)}</td>
            <td>
                <span class="text-{bar_color} fw-bold">{avg:.2f}</span>
                <div class="progress mt-1" style="height:4px;"><div class="progress-bar bg-{bar_color}" style="width:{int(avg*100)}%"></div></div>
            </td>
            <td>{fs.get("fail_count", 0)}</td>
        </tr>
        """

    # ── 门禁状态 ──
    release_blocked = data.get("release_blocked", False)
    gate_html = ""
    if release_blocked:
        blocking = ", ".join(data.get("blocking_tags", []))
        gate_label = "发布已阻断" if is_zh else "Release Blocked"
        gate_html = f'<div class="alert alert-danger mt-3"><strong>🚫 {gate_label}</strong>: {esc(blocking)}</div>'

    return f"""
<!DOCTYPE html>
<html lang="{"zh" if is_zh else "en"}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{L["title"]}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {{ background: #f8f9fa; }}
        .card-header[data-bs-toggle] .bi-chevron-down {{
            transition: transform 0.2s;
        }}
        .card-header[data-bs-toggle][aria-expanded="true"] .bi-chevron-down {{
            transform: rotate(180deg);
        }}
        .progress {{ background: #e9ecef; }}
    </style>
</head>
<body>
    <div class="container py-4" style="max-width: 1100px;">
        <h1 class="mb-4">🧬 {L["title"]}</h1>

        <!-- 概览 -->
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="card text-center h-100">
                    <div class="card-body">
                        <div class="display-4 text-{status_class} fw-bold">{pass_rate:.1%}</div>
                        <div class="text-muted">{L["pass_rate"]}</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center h-100">
                    <div class="card-body">
                        <div class="display-6">{data.get("total", 0)}</div>
                        <div class="text-muted">{L["total"]}</div>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card text-center h-100 border-success">
                    <div class="card-body">
                        <div class="display-6 text-success">{data.get("passed", 0)}</div>
                        <div class="text-muted">{L["passed"]}</div>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card text-center h-100 border-danger">
                    <div class="card-body">
                        <div class="display-6 text-danger">{data.get("failed", 0)}</div>
                        <div class="text-muted">{L["failed"]}</div>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card text-center h-100 border-warning">
                    <div class="card-body">
                        <div class="display-6 text-warning">{data.get("error", 0)}</div>
                        <div class="text-muted">{L["error"]}</div>
                    </div>
                </div>
            </div>
        </div>

        {gate_html}

        <!-- 因子汇总 -->
        {"" if not data.get("factor_summary") else f'''
        <div class="card mb-4">
            <div class="card-header"><h5 class="mb-0">{L["factor_summary"]}</h5></div>
            <div class="card-body p-0">
                <table class="table table-sm mb-0">
                    <thead><tr>
                        <th>{L["factor"]}</th><th>{L["activated"]}</th><th>{L["avg_score"]}</th><th>{L["fail_count"]}</th>
                    </tr></thead>
                    <tbody>{factor_summary_html}</tbody>
                </table>
            </div>
        </div>
        '''}

        <!-- 标签统计 -->
        {"" if not data.get("stats_by_tag") else f'''
        <div class="card mb-4">
            <div class="card-header"><h5 class="mb-0">{L["tag_stats"]}</h5></div>
            <div class="card-body p-0">
                <table class="table table-sm mb-0">
                    <thead><tr>
                        <th>{L["tag"]}</th><th>{L["total"]}</th><th>{L["passed"]}</th><th>{L["failed"]}</th>
                        <th>{L["pass_rate"]}</th><th>{L["threshold"]}</th><th>{L["meets"]}</th>
                    </tr></thead>
                    <tbody>{tag_stats_html}</tbody>
                </table>
            </div>
        </div>
        '''}

        <!-- 详细结果 -->
        <h3 class="mb-3">{L["detailed"]}</h3>
        <p class="text-muted mb-3"><small><i class="bi bi-info-circle"></i> {L["click_expand"]}</small></p>
        {results_html}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
