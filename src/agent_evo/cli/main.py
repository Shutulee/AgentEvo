"""AgentEvo CLI 主入口"""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from agent_evo import __version__

app = typer.Typer(
    name="agent-evo",
    help="AgentEvo - LLM Agent 自动化评测与优化框架",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"AgentEvo version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", callback=version_callback, is_eager=True, help="显示版本号"),
):
    """AgentEvo - LLM Agent 自动化评测与优化框架"""
    pass


@app.command()
def init(
    path: str = typer.Argument(".", help="项目路径"),
    template: str = typer.Option("basic", "-t", "--template", help="模板类型"),
):
    """初始化 AgentEvo 配置"""
    from agent_evo.cli.commands.init import run_init
    run_init(path, template)


@app.command(name="eval")
def eval_cmd(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径"),
    tags: Optional[str] = typer.Option(None, "-t", "--tags", help="只运行指定 tag（逗号分隔）"),
    tier: Optional[str] = typer.Option(None, "--tier", help="只运行指定层级: gold/silver"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="报告输出路径"),
):
    """运行评测（不优化）"""
    from agent_evo.cli.commands.eval import run_eval
    tag_list = tags.split(",") if tags else None
    asyncio.run(run_eval(config, tag_list, output, tier))


@app.command()
def run(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径"),
    tags: Optional[str] = typer.Option(None, "-t", "--tags", help="只运行指定 tag（逗号分隔）"),
    tier: Optional[str] = typer.Option(None, "--tier", help="只运行指定层级: gold/silver"),
    fix: bool = typer.Option(False, "--fix", help="自动修复失败用例"),
    pr: bool = typer.Option(False, "--pr", help="创建 PR"),
    dry_run: bool = typer.Option(False, "--dry-run", help="预览模式，不实际修改"),
):
    """运行完整流程（评测 + 优化 + PR）"""
    from agent_evo.cli.commands.run import run_pipeline
    tag_list = tags.split(",") if tags else None
    asyncio.run(run_pipeline(config, tag_list, fix, pr, dry_run, tier))


@app.command()
def report(
    input_file: str = typer.Argument(..., help="报告 JSON 文件路径"),
    format: str = typer.Option("terminal", "-f", "--format", help="输出格式: terminal, html, json"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="输出文件路径"),
):
    """查看/转换评测报告"""
    from agent_evo.cli.commands.report import show_report
    show_report(input_file, format, output)


@app.command()
def mutate(
    seed: str = typer.Option(..., "--seed", help="种子用例 YAML 文件路径"),
    count: int = typer.Option(3, "--count", help="每条种子生成数量"),
    output: str = typer.Option("./tests/silver_generated.yaml", "-o", "--output", help="输出文件路径"),
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径"),
):
    """基于黄金集变异扩充测评集"""
    from agent_evo.cli.commands.mutate import run_mutate
    asyncio.run(run_mutate(config, seed, count, output))


@app.command()
def review(
    status: str = typer.Option("pending", "--status", help="筛选状态: pending/approved/rejected"),
    approve_all: bool = typer.Option(False, "--approve-all", help="全部通过"),
    interactive: bool = typer.Option(False, "--interactive", help="逐条交互式审核"),
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径"),
):
    """查看/审核待审核用例"""
    from agent_evo.cli.commands.review import run_review
    run_review(config, status, approve_all, interactive)


@app.command(name="import")
def import_cmd(
    file: str = typer.Option(..., "--file", help="导入文件路径"),
    format: str = typer.Option("jsonl", "--format", help="文件格式: jsonl/csv/yaml"),
    output: str = typer.Option("./tests/production.yaml", "-o", "--output", help="输出文件路径"),
    auto_refine: bool = typer.Option(True, "--auto-refine/--no-auto-refine", help="自动提炼为标准 TestCase"),
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径"),
):
    """从线上数据导入测评集"""
    from agent_evo.cli.commands.import_cmd import run_import
    asyncio.run(run_import(config, file, format, output, auto_refine))


@app.command(name="gate-check")
def gate_check(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径"),
):
    """发布前门禁检查"""
    from agent_evo.cli.commands.gate_check import run_gate_check
    asyncio.run(run_gate_check(config))


@app.command()
def stats(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径"),
):
    """查看测评集统计"""
    from agent_evo.cli.commands.stats import run_stats
    run_stats(config)


if __name__ == "__main__":
    app()
