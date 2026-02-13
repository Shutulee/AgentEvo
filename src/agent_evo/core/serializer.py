"""TestCase 序列化：Model → YAML 写入
TestCase serialization: Model → YAML writing"""

from pathlib import Path
from typing import Optional

import yaml

from agent_evo.models.test_case import TestCase, TestSuite


def test_cases_to_yaml(
    cases: list[TestCase],
    name: str = "Generated Test Cases",
    description: Optional[str] = None,
) -> str:
    """将 TestCase 列表序列化为 YAML 字符串 / Serialize TestCase list to YAML string"""
    suite_dict = {"name": name}
    if description:
        suite_dict["description"] = description

    suite_dict["cases"] = []
    for case in cases:
        case_dict = _case_to_dict(case)
        suite_dict["cases"].append(case_dict)

    return yaml.dump(suite_dict, allow_unicode=True, default_flow_style=False, sort_keys=False)


def save_test_cases(
    cases: list[TestCase],
    output_path: str,
    name: str = "Generated Test Cases",
    description: Optional[str] = None,
) -> Path:
    """将 TestCase 列表写入 YAML 文件 / Write TestCase list to YAML file"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = test_cases_to_yaml(cases, name, description)
    path.write_text(content, encoding="utf-8")
    return path


def load_test_cases_from_yaml(file_path: str) -> list[TestCase]:
    """从 YAML 文件加载 TestCase 列表 / Load TestCase list from YAML file"""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "cases" not in data:
        return []

    return [TestCase(**c) for c in data["cases"]]


def _case_to_dict(case: TestCase) -> dict:
    """将 TestCase 转为简洁的字典（省略默认值字段）
    Convert TestCase to concise dict (omit default value fields)"""
    d: dict = {"id": case.id, "name": case.name}

    # input
    if isinstance(case.input, str):
        d["input"] = case.input
    else:
        d["input"] = case.input.model_dump(exclude_none=True)

    # expected_output
    if case.expected_output:
        d["expected_output"] = case.expected_output

    # 额外的精确校验规则（排除 output 避免重复）
    # Additional precise validation rules (exclude output to avoid duplication)
    expected = case.expected.model_dump(exclude_none=True)
    expected.pop("output", None)
    if expected:
        d["expected"] = expected

    # tags
    if case.tags:
        d["tags"] = case.tags

    # 非默认值的新增字段 / Non-default additional fields
    if case.tier.value != "gold":
        d["tier"] = case.tier.value
    if case.source.value != "manual":
        d["source"] = case.source.value
    if case.review_status.value != "approved":
        d["review_status"] = case.review_status.value
    if case.parent_id:
        d["parent_id"] = case.parent_id
    if case.mutation_strategy:
        d["mutation_strategy"] = case.mutation_strategy
    if case.bad_output:
        d["bad_output"] = case.bad_output
    if case.judge_hints:
        d["judge_hints"] = case.judge_hints

    return d
