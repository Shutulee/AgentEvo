"""mutate 命令：变异扩充测评集"""

from rich.console import Console

from agent_evo.core.config import load_config
from agent_evo.core.mutator import Mutator
from agent_evo.core.serializer import load_test_cases_from_yaml, save_test_cases

console = Console()


async def run_mutate(config_path: str, seed_path: str, count: int, output_path: str):
    """基于种子用例变异扩充"""
    try:
        config = load_config(config_path)
        mutator = Mutator(config)

        # 加载种子用例
        seeds = load_test_cases_from_yaml(seed_path)
        if not seeds:
            console.print(f"[red]未找到种子用例: {seed_path}[/red]")
            raise SystemExit(1)

        console.print(f"加载了 {len(seeds)} 条种子用例")
        console.print(f"每条种子生成 {count} 个变异...\n")

        # 变异
        mutations = await mutator.mutate(seeds, count_per_case=count)
        console.print(f"生成了 {len(mutations)} 条变异用例")

        # LLM 预审
        if config.mutation.auto_review:
            console.print("LLM 预审中...")
            mutations = await mutator.review_batch(mutations)
            rejected = sum(1 for m in mutations if m.review_status.value == "rejected")
            if rejected:
                console.print(f"[yellow]预审拒绝 {rejected} 条[/yellow]")

        # 写入文件
        approved = [m for m in mutations if m.review_status.value != "rejected"]
        path = save_test_cases(
            approved, output_path,
            name="变异生成测评集",
            description=f"基于 {seed_path} 变异生成",
        )
        console.print(f"\n[green]已写入 {len(approved)} 条用例到 {path}[/green]")
        console.print(f"[yellow]所有用例状态为 pending，请通过 agent-evo review 审核[/yellow]")

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
