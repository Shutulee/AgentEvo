"""mutate 命令：变异扩充测评集
mutate command: expand test suite via mutation"""

from rich.console import Console

from agent_evo.core.config import load_config
from agent_evo.core.mutator import Mutator
from agent_evo.core.serializer import load_test_cases_from_yaml, save_test_cases
from agent_evo.utils.i18n import t

console = Console()


async def run_mutate(config_path: str, seed_path: str, count: int, output_path: str):
    """基于种子用例变异扩充 / Expand test suite based on seed cases"""
    try:
        config = load_config(config_path)
        mutator = Mutator(config)

        # 加载种子用例 / Load seed cases
        seeds = load_test_cases_from_yaml(seed_path)
        if not seeds:
            console.print(f"[red]{t('config_file_missing').format(path=seed_path)}[/red]")
            raise SystemExit(1)

        console.print(t("loaded_seeds").format(n=len(seeds)))
        console.print(t("mutate_per_seed").format(n=count))
        console.print()

        # 变异 / Mutate
        mutations = await mutator.mutate(seeds, count_per_case=count)
        console.print(t("generated_mutations").format(n=len(mutations)))

        # LLM 预审 / LLM pre-review
        if config.mutation.auto_review:
            console.print(t("llm_reviewing"))
            mutations = await mutator.review_batch(mutations)
            rejected = sum(1 for m in mutations if m.review_status.value == "rejected")
            if rejected:
                console.print(f"[yellow]{t('review_rejected').format(n=rejected)}[/yellow]")

        # 写入文件 / Write to file
        approved = [m for m in mutations if m.review_status.value != "rejected"]
        path = save_test_cases(
            approved, output_path,
            name="Mutation Generated / 变异生成测评集",
            description=f"Mutated from / 基于 {seed_path} 变异生成",
        )
        console.print(f"\n[green]{t('written_cases').format(n=len(approved), path=path)}[/green]")
        console.print(f"[yellow]{t('mutate_review_hint')}[/yellow]")

    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
