"""AgentEvo CLI 主入口"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from agent_evo import __version__

app = typer.Typer(
    name="agent-evo",
    help="🧬 AgentEvo - LLM Agent 自动化评测与优化框架",
    add_completion=False
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"AgentEvo version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="显示版本号"
    )
):
    """AgentEvo - LLM Agent 自动化评测与优化框架"""
    pass


@app.command()
def init(
    path: str = typer.Argument(".", help="项目路径"),
    template: str = typer.Option("basic", "-t", "--template", help="模板类型")
):
    """初始化 AgentEvo 配置"""
    from agent_evo.cli.commands.init import run_init
    run_init(path, template)


@app.command()
def eval(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径"),
    tags: Optional[str] = typer.Option(None, "-t", "--tags", help="只运行指定 tag（逗号分隔）"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="报告输出路径")
):
    """运行评测（不优化）"""
    from agent_evo.cli.commands.eval import run_eval
    
    tag_list = tags.split(",") if tags else None
    asyncio.run(run_eval(config, tag_list, output))


@app.command()
def run(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径"),
    tags: Optional[str] = typer.Option(None, "-t", "--tags", help="只运行指定 tag（逗号分隔）"),
    fix: bool = typer.Option(False, "--fix", help="自动修复失败用例"),
    pr: bool = typer.Option(False, "--pr", help="创建 PR"),
    dry_run: bool = typer.Option(False, "--dry-run", help="预览模式，不实际修改")
):
    """运行完整流程（评测 + 优化 + PR）"""
    from agent_evo.cli.commands.run import run_pipeline
    
    tag_list = tags.split(",") if tags else None
    asyncio.run(run_pipeline(config, tag_list, fix, pr, dry_run))


@app.command()
def report(
    input_file: str = typer.Argument(..., help="报告 JSON 文件路径"),
    format: str = typer.Option("terminal", "-f", "--format", help="输出格式: terminal, html, json"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="输出文件路径")
):
    """查看/转换评测报告"""
    from agent_evo.cli.commands.report import show_report
    show_report(input_file, format, output)


if __name__ == "__main__":
    app()
