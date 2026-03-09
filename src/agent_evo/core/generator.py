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
from agent_evo.adapters.http import HttpAdapter
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
        agent_type = self.config.agent.type

        if agent_type == "http":
            return self._create_http_adapter()
        else:
            return self._create_callable_adapter()

    def _create_http_adapter(self) -> AgentAdapter:
        """创建 HTTP 适配器 / Create HTTP adapter"""
        http_config = self.config.agent.http

        prompt_file = None
        if self.config.agent.prompt_file:
            prompt_file = str(self.project_dir / self.config.agent.prompt_file)

        return HttpAdapter(
            url=http_config.url,
            method=http_config.method,
            headers=http_config.headers,
            body_template=http_config.body,
            response_path=http_config.response_path,
            stream=http_config.stream,
            stream_event_field=http_config.stream_event_field,
            stream_content_field=http_config.stream_content_field,
            stream_done_event=http_config.stream_done_event,
            stream_text_events=http_config.stream_text_events,
            timeout=http_config.timeout,
            prompt_file=prompt_file,
        )

    def _create_callable_adapter(self) -> AgentAdapter:
        """创建 Callable 适配器 / Create Callable adapter"""
        module_path = self.config.agent.module
        func_name = self.config.agent.function

        try:
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

    def load_test_cases(
        self,
        tags: Optional[list[str]] = None,
        include_silver: bool = False,
    ) -> list[TestCase]:
        """加载测试用例（默认只加载黄金集，可选包含白银集）
        Load test cases (gold only by default, optionally include silver)

        黄金集路径由 config.test_cases 指定，白银集由 config.silver_test_cases 指定。
        Gold set path from config.test_cases, silver set from config.silver_test_cases.
        只有 review_status == approved 的用例才参与评测。
        Only cases with review_status == approved are included in evaluation.
        """
        from agent_evo.models.test_case import ReviewStatus, TestCaseTier

        # 收集需要扫描的 glob 路径 / Collect glob patterns to scan
        patterns = [str(self.project_dir / self.config.test_cases)]
        if include_silver:
            patterns.append(str(self.project_dir / self.config.silver_test_cases))

        cases = []
        for pattern in patterns:
            files = glob(str(pattern), recursive=True)
            # 根据路径判断 tier / Determine tier from pattern
            is_silver_pattern = (pattern == str(self.project_dir / self.config.silver_test_cases))

            for file_path in files:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not data or "cases" not in data:
                    continue

                suite = TestSuite(**data)
                for case_data in suite.cases:
                    if isinstance(case_data, dict):
                        case = TestCase(**case_data)
                    else:
                        case = case_data

                    # 根据目录自动设置 tier / Auto-set tier based on directory
                    if is_silver_pattern:
                        case.tier = TestCaseTier.SILVER

                    # 跳过未审核通过的用例 / Skip unapproved cases
                    if case.review_status != ReviewStatus.APPROVED:
                        continue

                    # 按 tag 过滤 / Filter by tag
                    if tags:
                        if any(tag in case.tags for tag in tags):
                            cases.append(case)
                    else:
                        cases.append(case)

        return cases

    def _build_context(self, case: TestCase) -> dict[str, Any]:
        """构建上下文，自动注入 LLM 配置 / Build context with LLM config injected"""
        context = case.input_context or {}

        # 将 agent-evo.yaml 中的 llm 配置注入 context
        # 这样 Agent 函数可以直接从 context 获取 LLM 配置，无需硬编码
        if self.config.llm:
            llm_config = {
                "provider": self.config.llm.provider,
                "model": self.config.llm.model,
                "api_key": self.config.llm.api_key,
            }
            if self.config.llm.base_url:
                llm_config["base_url"] = self.config.llm.base_url
            context["llm"] = llm_config

        return context

    async def run_case(self, case: TestCase) -> GeneratorResult:
        """运行单个测试用例 / Run a single test case"""
        start_time = time.time()

        try:
            output = await self.adapter.invoke(
                input=case.input_query,
                context=self._build_context(case)
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
