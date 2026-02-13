"""测试用例模型"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator


# ─── 枚举 ───────────────────────────────────────────────

class TestCaseTier(str, Enum):
    """评测集层级"""
    GOLD = "gold"       # 黄金集：人工精审
    SILVER = "silver"   # 白银集：AI 生成 + 人工抽审


class TestCaseSource(str, Enum):
    """用例来源"""
    MANUAL = "manual"           # 人工编写
    MUTATION = "mutation"       # 变异生成
    PRODUCTION = "production"   # 线上收集


class ReviewStatus(str, Enum):
    """审核状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ─── 校验规则模型 ────────────────────────────────────────

class JsonPathAssertion(BaseModel):
    """JSONPath 校验规则"""
    path: str = Field(..., description="JSONPath 表达式，如 $.action")
    operator: str = Field(default="eq", description="比较算子：eq/neq/in/contains/exists/regex")
    value: Any = Field(default=None, description="期望值")


class ToolCallAssertion(BaseModel):
    """工具调用校验规则"""
    tool_name: str = Field(..., description="工具名称")
    required_params: Optional[dict[str, Any]] = Field(default=None, description="必须包含的参数及其值")
    param_source: Optional[dict[str, str]] = Field(default=None, description="参数来源约束")


class ToolCallConstraints(BaseModel):
    """工具调用链约束"""
    ordered: bool = Field(default=False, description="是否要求严格顺序")
    required_sequence: Optional[list[str]] = Field(default=None, description="必须出现的调用序列")
    forbidden_tools: Optional[list[str]] = Field(default=None, description="禁止调用的工具")
    max_calls: Optional[int] = Field(default=None, description="最大调用次数限制")


# ─── 期望输出 ────────────────────────────────────────────

class ExpectedOutput(BaseModel):
    """期望输出

    用户只需写 output（理想回答），框架自动从内容准确性、行为正确性、
    结构完整性三个维度用 LLM 评判。

    如果需要额外的精确校验（如检查关键词、校验 JSON 格式），可以补充
    下方的可选字段，框架会在 LLM 评判之外叠加这些确定性检查。
    """

    # --- 理想回答（必填，框架自动评判的核心依据）---
    output: Optional[str] = Field(default=None, description="理想的 Agent 回答")

    # --- 可选：额外的精确校验规则 ---
    # 结构校验
    json_schema: Optional[dict] = Field(default=None, description="JSON Schema 校验")
    schema_file: Optional[str] = Field(default=None, description="JSON Schema 文件路径")
    exact_json: Optional[dict] = Field(default=None, description="精确 JSON 匹配")
    json_path_assertions: Optional[list[JsonPathAssertion]] = Field(default=None, description="JSONPath 校验规则")

    # 行为校验
    behavior: Optional[str] = Field(default=None, description="期望行为：refuse, ask_clarification 等")
    behavior_hint: Optional[str] = Field(default=None, description="行为评判提示")
    required_tool_calls: Optional[list[ToolCallAssertion]] = Field(default=None, description="必须出现的工具调用")
    tool_call_constraints: Optional[ToolCallConstraints] = Field(default=None, description="工具调用链约束")

    # 内容校验
    contains: Optional[list[str]] = Field(default=None, description="回答中应包含的关键词")
    not_contains: Optional[list[str]] = Field(default=None, description="回答中不应包含的关键词")
    semantic_criteria: Optional[list[str]] = Field(default=None, description="语义评判标准")

    # 自定义校验
    validator: Optional[str] = Field(default=None, description="自定义校验函数路径")


# ─── 输入模型 ────────────────────────────────────────────

class TestCaseInput(BaseModel):
    """测试用例输入"""
    query: str = Field(..., description="用户输入")
    context: Optional[dict[str, Any]] = Field(default=None, description="额外上下文")


# ─── 测试用例 ────────────────────────────────────────────

class TestCase(BaseModel):
    """单个测试用例

    写法：给一个输入，写一个理想回答（expected_output），框架自动评判。
    """
    id: str = Field(..., description="用例 ID")
    name: str = Field(..., description="用例名称")
    input: str | TestCaseInput = Field(..., description="输入")

    # 理想回答
    expected_output: Optional[str] = Field(default=None, description="理想的 Agent 回答")
    # 内部使用（expected_output 会自动同步到 expected.output）
    expected: ExpectedOutput = Field(default_factory=ExpectedOutput, description="期望输出详情")

    tags: list[str] = Field(default_factory=list, description="标签")
    judge_hints: Optional[str] = Field(default=None, description="给评判器的额外提示")

    # --- 新增字段（均有默认值，向后兼容）---
    source: TestCaseSource = Field(default=TestCaseSource.MANUAL, description="用例来源")
    parent_id: Optional[str] = Field(default=None, description="变异来源用例 ID")
    mutation_strategy: Optional[str] = Field(default=None, description="LLM 选择的变异方式（自由文本）")
    review_status: ReviewStatus = Field(default=ReviewStatus.APPROVED, description="审核状态")
    tier: TestCaseTier = Field(default=TestCaseTier.GOLD, description="评测集层级")
    bad_output: Optional[str] = Field(default=None, description="错误输出（线上采集的 Agent 原始错误回复）")

    @model_validator(mode="after")
    def sync_expected_output(self) -> "TestCase":
        """将顶级 expected_output 同步到 expected.output"""
        if self.expected_output and not self.expected.output:
            self.expected.output = self.expected_output
        elif self.expected.output and not self.expected_output:
            self.expected_output = self.expected.output
        return self

    @property
    def input_query(self) -> str:
        """获取输入查询字符串"""
        if isinstance(self.input, str):
            return self.input
        return self.input.query

    @property
    def input_context(self) -> Optional[dict[str, Any]]:
        """获取输入上下文"""
        if isinstance(self.input, str):
            return None
        return self.input.context


# ─── 测试套件 ────────────────────────────────────────────

class TestSuite(BaseModel):
    """测试套件"""
    name: str = Field(..., description="套件名称")
    description: Optional[str] = Field(default=None)
    context: Optional[dict[str, Any]] = Field(default=None, description="全局上下文")
    cases: list[TestCase] = Field(..., description="测试用例列表")
    tier: Optional[TestCaseTier] = Field(default=None, description="套件级别的默认层级")
