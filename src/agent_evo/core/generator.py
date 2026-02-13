"""测试执行器 / Test executor"""

import asyncio
import importlib
import time
from glob import glob
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from agent_evo.models import Config, TestCase, TestSuite
from agent_evo.adapters.base import AgentAdapter
from agent_evo.adapters.callable import CallableAdapter
from agent_evo.utils.i18n import t


class GeneratorResult:
    """执行结果（未评判）/ Execution result (not yet evaluated)"""

    def __init__(self, case: TestCase, output: str, execution_time_ms: int, error: Optional[str] = None):
        self.case = case
        self.output = output
        self.execution_time_ms = execution_time_ms
        self.error = error


class Generator:
    """测试执行器 / Test executor"""

    def __init__(self, config: Config, project_dir: Path):
        self.config = config
        self.project_dir = project_dir
        self.adapter = self._create_adapter()

    def _create_adapter(self) -> AgentAdapter:
        """创建 Agent 适配器 / Create Agent adapter"""
        # 动态加载用户的 Agent 模块 / Dynamically load user's Agent module
        module_path = self.config.agent.module
        func_name = self.config.agent.function

        try:
            # 尝试相对于项目目录导入 / Try importing relative to project directory
            import sys
            sys.path.insert(0, str(self.project_dir))

            module = importlib.import_module(module_path)
            func = getattr(module, func_name)

            prompt_file = self.project_dir / self.config.agent.prompt_file

            return CallableAdapter(
                func=func,
                prompt_file=str(prompt_file)
            )
        except (ImportError, AttributeError) as e:
            raise RuntimeError(
                t("agent_load_fail").format(path=f"{module_path}.{func_name}", err=e)
            )

    def load_test_cases(self, tags: Optional[list[str]] = None) -> list[TestCase]:
        """加载测试用例 / Load test cases"""
        pattern = self.project_dir / self.config.test_cases
        files = glob(str(pattern), recursive=True)

        cases = []
        for file_path in files:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            suite = TestSuite(**data)
            for case_data in suite.cases:
                if isinstance(case_data, dict):
                    case = TestCase(**case_data)
                else:
                    case = case_data

                # 按 tag 过滤 / Filter by tag
                if tags:
                    if any(tag in case.tags for tag in tags):
                        cases.append(case)
                else:
                    cases.append(case)

        return cases

    async def run_case(self, case: TestCase) -> GeneratorResult:
        """运行单个测试用例 / Run a single test case"""
        start_time = time.time()

        try:
            output = await self.adapter.invoke(
                input=case.input_query,
                context=case.input_context
            )
            execution_time_ms = int((time.time() - start_time) * 1000)

            return GeneratorResult(
                case=case,
                output=output,
                execution_time_ms=execution_time_ms
            )
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return GeneratorResult(
                case=case,
                output="",
                execution_time_ms=execution_time_ms,
                error=str(e)
            )

    async def run_all(
        self,
        cases: list[TestCase],
        concurrency: int = 5
    ) -> list[GeneratorResult]:
        """并发运行所有测试用例 / Run all test cases concurrently"""
        semaphore = asyncio.Semaphore(concurrency)

        async def run_with_semaphore(case: TestCase) -> GeneratorResult:
            async with semaphore:
                return await self.run_case(case)

        results = await asyncio.gather(
            *[run_with_semaphore(case) for case in cases],
            return_exceptions=True
        )

        # 处理异常 / Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(GeneratorResult(
                    case=cases[i],
                    output="",
                    execution_time_ms=0,
                    error=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results
