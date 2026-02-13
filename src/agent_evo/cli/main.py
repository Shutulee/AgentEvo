"""AgentEvo CLI 主入口 / AgentEvo CLI main entry"""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from agent_evo import __version__

app = typer.Typer(
    name="agent-evo",
    help="AgentEvo - LLM Agent 自动化评测与优化框架 / LLM Agent automated evaluation and optimization framework",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"AgentEvo version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", callback=version_callback, is_eager=True, help="显示版本号 / Show version"),
):
    """AgentEvo - LLM Agent 自动化评测与优化框架 / LLM Agent automated evaluation and optimization framework"""
    pass


@app.command()
def init(
    path: str = typer.Argument(".", help="项目路径 / Project path"),
    template: str = typer.Option("basic", "-t", "--template", help="模板类型 / Template type"),
):
    """初始化 AgentEvo 配置 / Initialize AgentEvo configuration"""
    from agent_evo.cli.commands.init import run_init
    run_init(path, template)


@app.command(name="eval")
def eval_cmd(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径 / Config file path"),
    tags: Optional[str] = typer.Option(None, "-t", "--tags", help="只运行指定 tag（逗号分隔）/ Run specified tags only (comma separated)"),
    tier: Optional[str] = typer.Option(None, "--tier", help="只运行指定层级 / Run specified tier only: gold/silver"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="报告输出路径 / Report output path"),
):
    """运行评测（不优化）/ Run evaluation (no optimization)"""
    from agent_evo.cli.commands.eval import run_eval
    tag_list = tags.split(",") if tags else None
    asyncio.run(run_eval(config, tag_list, output, tier))


@app.command()
def run(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径 / Config file path"),
    tags: Optional[str] = typer.Option(None, "-t", "--tags", help="只运行指定 tag（逗号分隔）/ Run specified tags only (comma separated)"),
    tier: Optional[str] = typer.Option(None, "--tier", help="只运行指定层级 / Run specified tier only: gold/silver"),
    fix: bool = typer.Option(False, "--fix", help="自动修复失败用例 / Auto-fix failed cases"),
    pr: bool = typer.Option(False, "--pr", help="创建 PR / Create PR"),
    dry_run: bool = typer.Option(False, "--dry-run", help="预览模式，不实际修改 / Preview mode, no actual modifications"),
):
    """运行完整流程（评测 + 优化 + PR）/ Run full pipeline (eval + optimize + PR)"""
    from agent_evo.cli.commands.run import run_pipeline
    tag_list = tags.split(",") if tags else None
    asyncio.run(run_pipeline(config, tag_list, fix, pr, dry_run, tier))


@app.command()
def report(
    input_file: str = typer.Argument(..., help="报告 JSON 文件路径 / Report JSON file path"),
    format: str = typer.Option("terminal", "-f", "--format", help="输出格式 / Output format: terminal, html, json"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="输出文件路径 / Output file path"),
):
    """查看/转换评测报告 / View/convert evaluation report"""
    from agent_evo.cli.commands.report import show_report
    show_report(input_file, format, output)


@app.command()
def mutate(
    seed: str = typer.Option(..., "--seed", help="种子用例 YAML 文件路径 / Seed case YAML file path"),
    count: int = typer.Option(3, "--count", help="每条种子生成数量 / Number of mutations per seed"),
    output: str = typer.Option("./tests/silver_generated.yaml", "-o", "--output", help="输出文件路径 / Output file path"),
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径 / Config file path"),
):
    """基于黄金集变异扩充测评集 / Expand test suite via mutation from gold set"""
    from agent_evo.cli.commands.mutate import run_mutate
    asyncio.run(run_mutate(config, seed, count, output))


@app.command()
def review(
    status: str = typer.Option("pending", "--status", help="筛选状态 / Filter status: pending/approved/rejected"),
    approve_all: bool = typer.Option(False, "--approve-all", help="全部通过 / Approve all"),
    interactive: bool = typer.Option(False, "--interactive", help="逐条交互式审核 / Interactive review one by one"),
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径 / Config file path"),
):
    """查看/审核待审核用例 / View/review pending cases"""
    from agent_evo.cli.commands.review import run_review
    run_review(config, status, approve_all, interactive)


@app.command(name="import")
def import_cmd(
    file: str = typer.Option(..., "--file", help="导入文件路径 / Import file path"),
    format: str = typer.Option("jsonl", "--format", help="文件格式 / File format: jsonl/csv/yaml"),
    output: str = typer.Option("./tests/production.yaml", "-o", "--output", help="输出文件路径 / Output file path"),
    auto_refine: bool = typer.Option(True, "--auto-refine/--no-auto-refine", help="自动提炼为标准 TestCase / Auto-refine to standard TestCase"),
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径 / Config file path"),
):
    """从线上数据导入测评集 / Import test cases from production data"""
    from agent_evo.cli.commands.import_cmd import run_import
    asyncio.run(run_import(config, file, format, output, auto_refine))


@app.command(name="gate-check")
def gate_check(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径 / Config file path"),
):
    """发布前门禁检查 / Pre-release gate check"""
    from agent_evo.cli.commands.gate_check import run_gate_check
    asyncio.run(run_gate_check(config))


@app.command()
def stats(
    config: str = typer.Option("agent-evo.yaml", "-c", "--config", help="配置文件路径 / Config file path"),
):
    """查看测评集统计 / View test suite statistics"""
    from agent_evo.cli.commands.stats import run_stats
    run_stats(config)


if __name__ == "__main__":
    app()
