"""线上数据导入引擎 / Production data import engine"""

import csv
import json
import uuid
from pathlib import Path
from typing import Optional, Any

import yaml

from agent_evo.models import Config, TestCase
from agent_evo.models.test_case import TestCaseSource, TestCaseTier, ReviewStatus, ExpectedOutput
from agent_evo.models.import_models import ProductionRecord, ImportResult, APISourceConfig
from agent_evo.utils.llm import LLMClient
from agent_evo.utils.i18n import t


class TestCaseImporter:
    """测评集导入引擎 / Test case import engine"""

    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config.llm)
        self.refine_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompt_dir / "refine.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        return """你是一个测试用例提炼专家。基于线上 Bad Case 数据，生成标准的测试用例。
You are a test case refinement expert. Generate standard test cases based on production bad case data.

## 线上数据 / Production Data
- 用户输入 / User input: {query}
- Agent 错误回复 / Agent wrong response: {agent_response}
- 纠错信息 / Correction: {corrected_response}
- 错误类型 / Error type: {error_type}

## 任务 / Task
1. 分析 Agent 的回复"错在哪" / Analyze what went wrong with Agent's response
2. 生成一个理想的回答（expected_output）/ Generate an ideal answer (expected_output)
3. 自动打标签 / Auto-tag

## 输出格式（JSON）/ Output format (JSON)
{{
  "name": "用例名称 / Case name",
  "expected_output": "理想的 Agent 回答 / Ideal Agent response",
  "tags": ["regression", "其他标签 / other tags"]
}}"""

    # ── 格式解析 / Format parsing ────────────────────────────

    def parse_jsonl(self, file_path: str) -> list[ProductionRecord]:
        """解析 JSONL 文件 / Parse JSONL file"""
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    records.append(ProductionRecord(**data))
                except Exception:
                    pass
        return records

    def parse_csv(self, file_path: str, column_mapping: Optional[dict] = None) -> list[ProductionRecord]:
        """解析 CSV 文件 / Parse CSV file"""
        mapping = column_mapping or {
            "query": "query",
            "agent_response": "agent_response",
            "corrected_response": "corrected_response",
            "error_type": "error_type",
        }

        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    record_data = {}
                    for target, source in mapping.items():
                        if source in row:
                            record_data[target] = row[source]
                    if "query" in record_data and "agent_response" in record_data:
                        records.append(ProductionRecord(**record_data))
                except Exception:
                    pass
        return records

    def parse_yaml(self, file_path: str) -> list[ProductionRecord]:
        """解析 YAML 文件 / Parse YAML file"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if isinstance(data, list):
            return [ProductionRecord(**item) for item in data if isinstance(item, dict)]
        elif isinstance(data, dict) and "records" in data:
            return [ProductionRecord(**item) for item in data["records"]]
        return []

    # ── 导入流程 / Import workflow ────────────────────────────

    async def import_from_file(
        self,
        file_path: str,
        format: str = "jsonl",
        auto_refine: bool = True,
        column_mapping: Optional[dict] = None,
    ) -> tuple[list[TestCase], ImportResult]:
        """从文件导入 / Import from file"""
        # 解析 / Parse
        if format == "jsonl":
            records = self.parse_jsonl(file_path)
        elif format == "csv":
            records = self.parse_csv(file_path, column_mapping)
        elif format == "yaml":
            records = self.parse_yaml(file_path)
        else:
            return [], ImportResult(errors=[t("unsupported_format").format(fmt=format)])

        if not records:
            return [], ImportResult(errors=[t("no_valid_records")])

        return await self._refine_records(records, auto_refine)

    async def import_from_source(
        self,
        source: APISourceConfig,
        auto_refine: bool = True,
    ) -> tuple[list[TestCase], ImportResult]:
        """从 HTTP API 数据源拉取并导入 / Fetch from HTTP API source and import"""
        records = await self._fetch_from_api(source)

        if not records:
            return [], ImportResult(errors=[t("no_valid_records")])

        return await self._refine_records(records, auto_refine)

    # ── HTTP 数据源拉取 / HTTP data source fetching ──────────

    async def _fetch_from_api(self, source: APISourceConfig) -> list[ProductionRecord]:
        """从 HTTP API 拉取数据并映射为 ProductionRecord
        Fetch data from HTTP API and map to ProductionRecord"""
        import httpx

        all_records: list[ProductionRecord] = []
        pagination = source.pagination

        # 构建基础请求参数 / Build base request params
        base_params = dict(source.params)
        if source.filter:
            base_params.update(source.filter)

        page = 1
        cursor: Optional[str] = None

        async with httpx.AsyncClient(timeout=source.timeout) as client:
            while True:
                # 构建本次请求参数 / Build per-request params
                request_params = dict(base_params)
                if pagination:
                    if pagination.type == "page":
                        request_params[pagination.page_param] = page
                        request_params[pagination.size_param] = pagination.size
                    elif pagination.type == "offset":
                        request_params[pagination.page_param] = (page - 1) * pagination.size
                        request_params[pagination.size_param] = pagination.size
                    elif pagination.type == "cursor" and cursor:
                        param_name = pagination.cursor_param or pagination.page_param
                        request_params[param_name] = cursor

                # 发起请求 / Send request
                if source.method == "GET":
                    response = await client.get(
                        source.url,
                        headers=source.headers,
                        params=request_params,
                    )
                else:
                    response = await client.post(
                        source.url,
                        headers=source.headers,
                        json=request_params,
                    )

                response.raise_for_status()
                body = response.json()

                # 从响应中提取数据数组 / Extract data array from response
                data_list = self._extract_by_path(body, source.data_path)
                if not isinstance(data_list, list) or not data_list:
                    break

                # 字段映射 → ProductionRecord / Field mapping → ProductionRecord
                for item in data_list:
                    record = self._map_to_record(item, source.field_mapping)
                    if record:
                        all_records.append(record)

                # 分页控制 / Pagination control
                if not pagination:
                    break

                if pagination.type in ("page", "offset"):
                    # 检查是否还有下一页 / Check if there are more pages
                    if pagination.total_path:
                        total = self._extract_by_path(body, pagination.total_path)
                        if isinstance(total, (int, float)) and page * pagination.size >= total:
                            break
                    if len(data_list) < pagination.size:
                        break
                elif pagination.type == "cursor":
                    if not pagination.cursor_path:
                        break
                    next_cursor = self._extract_by_path(body, pagination.cursor_path)
                    if not next_cursor:
                        break
                    cursor = str(next_cursor)

                page += 1
                if page > pagination.max_pages:
                    break

        return all_records

    @staticmethod
    def _extract_by_path(data: Any, path: str) -> Any:
        """通过点分隔路径提取嵌套 JSON 值 / Extract nested JSON value by dot-separated path

        例如 / Example: _extract_by_path({"data": {"records": [...]}}, "data.records") → [...]
        """
        current = data
        for key in path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    @staticmethod
    def _map_to_record(item: dict, field_mapping: dict[str, str]) -> Optional[ProductionRecord]:
        """将 API 返回的字段映射为 ProductionRecord
        Map API response fields to ProductionRecord

        field_mapping 格式 / format: {AgentEvo字段: API字段}
        例如 / Example: {"query": "user_input", "agent_response": "bot_reply"}
        """
        mapped: dict[str, Any] = {}
        for target_field, source_field in field_mapping.items():
            # 支持点分隔路径 / Support dot-separated paths
            value = item
            for key in source_field.split("."):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            if value is not None:
                mapped[target_field] = value

        # 必填字段检查 / Required fields check
        if "query" not in mapped or "agent_response" not in mapped:
            return None

        try:
            return ProductionRecord(**mapped)
        except Exception:
            return None

    # ── 公共提炼流程 / Common refinement workflow ─────────────

    async def _refine_records(
        self,
        records: list[ProductionRecord],
        auto_refine: bool,
    ) -> tuple[list[TestCase], ImportResult]:
        """将 ProductionRecord 列表提炼为 TestCase / Refine ProductionRecord list to TestCase"""
        cases = []
        errors = []
        for record in records:
            try:
                if auto_refine:
                    case = await self.refine_to_test_case(record)
                else:
                    case = self._record_to_basic_case(record)
                cases.append(case)
            except Exception as e:
                errors.append(t("process_record_fail").format(err=e))

        result = ImportResult(
            total_records=len(records),
            imported=len(cases),
            pending_review=len(cases),
            errors=errors,
        )
        return cases, result

    async def refine_to_test_case(self, record: ProductionRecord) -> TestCase:
        """利用 LLM 将线上数据提炼为标准 TestCase
        Use LLM to refine production data into standard TestCase"""
        prompt = self.refine_prompt.format(
            query=record.query,
            agent_response=record.agent_response,
            corrected_response=record.corrected_response or "N/A",
            error_type=record.error_type or "unknown",
        )

        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        data = json.loads(response)

        import_cfg = self.config.import_config
        default_tags = import_cfg.default_tags if import_cfg else ["regression"]
        default_tier = import_cfg.default_tier if import_cfg else "silver"

        return TestCase(
            id=f"prod-{uuid.uuid4().hex[:8]}",
            name=data.get("name", f"Production case: {record.query[:30]}"),
            input=record.query,
            expected_output=data.get("expected_output"),
            expected=data.get("expected", {}),
            tags=data.get("tags", default_tags),
            source=TestCaseSource.PRODUCTION,
            review_status=ReviewStatus.PENDING,
            tier=TestCaseTier(default_tier),
            bad_output=record.agent_response,
        )

    @staticmethod
    def _record_to_basic_case(record: ProductionRecord) -> TestCase:
        """不调 LLM，简单转换为 TestCase / Simple conversion without LLM"""
        return TestCase(
            id=f"prod-{uuid.uuid4().hex[:8]}",
            name=f"Production case: {record.query[:30]}",
            input=record.query,
            expected=ExpectedOutput(),
            tags=["regression"],
            source=TestCaseSource.PRODUCTION,
            review_status=ReviewStatus.PENDING,
            tier=TestCaseTier.SILVER,
            bad_output=record.agent_response,
        )

    # ── 去重 / Deduplication ─────────────────────────────────

    async def deduplicate(
        self,
        new_cases: list[TestCase],
        existing_cases: list[TestCase],
    ) -> list[TestCase]:
        """基于简单文本相似度去重（避免引入重型依赖）
        Simple text-based deduplication (avoids heavy dependencies)"""
        existing_inputs = {c.input_query.strip().lower() for c in existing_cases}
        unique = []
        for case in new_cases:
            normalized = case.input_query.strip().lower()
            if normalized not in existing_inputs:
                unique.append(case)
                existing_inputs.add(normalized)
        return unique
