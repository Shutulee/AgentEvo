"""run 命令"""

from typing import Optional

from rich.console import Console

from agent_evo.core.config import load_config
from agent_evo.core.pipeline import Pipeline

console = Console()


async def run_pipeline(
    config_path: str,
    tags: Optional[list[str]],
    auto_fix: bool,
    create_pr: bool,
    dry_run: bool
):
    """运行完整流程"""
    try:
        # 加载配置
        config = load_config(config_path)
        
        # 创建 Pipeline
        pipeline = Pipeline(config)
        
        # 运行
        result = await pipeline.run(
            auto_fix=auto_fix,
            create_pr=create_pr,
            tags=tags,
            dry_run=dry_run
        )
        
        # 显示最终状态
        console.print("\n" + "=" * 50)
        if result.success:
            console.print("[bold green]✅ Pipeline 执行成功[/bold green]")
        else:
            console.print("[bold red]❌ Pipeline 执行完成，存在失败用例[/bold red]")
        
        if result.pr_url:
            console.print(f"\n🔗 PR: {result.pr_url}")
        
        console.print()
        
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]❌ 执行失败: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
