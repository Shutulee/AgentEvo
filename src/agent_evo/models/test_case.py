"""测试用例模型 / Test case models"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator


# ─── 枚举 / Enumerations ────────────────────────────────

class TestCaseTier(str, Enum):
    """评测集层级 / Test set tier"""
    GOLD = "gold"       # 黄金集：人工精审 / Gold set: manually reviewed
    SILVER = "silver"   # 白银集：AI 生成 + 人工抽审 / Silver set: AI generated + spot-checked


class TestCaseSource(str, Enum):
    """用例来源 / Test case source"""
    MANUAL = "manual"           # 人工编写 / Manually written
    MUTATION = "mutation"       # 变异生成 / Mutation generated
    PRODUCTION = "production"   # 线上收集 / Collected from production


class ReviewStatus(str, Enum):
    """审核状态 / Review status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ─── 校验规则模型 / Validation rule models ───────────────

class JsonPathAssertion(BaseModel):
    """JSONPath 校验规则 / JSONPath validation rule"""
    path: str = Field(..., description="JSONPath 表达式，如 $.action / JSONPath expression, e.g. $.action")
    operator: str = Field(default="eq", description="比较算子：eq/neq/in/contains/exists/regex / Comparison operator")
    value: Any = Field(default=None, description="期望值 / Expected value")


class ToolCallAssertion(BaseModel):
    """工具调用校验规则 / Tool call validation rule"""
    tool_name: str = Field(..., description="工具名称 / Tool name")
    required_params: Optional[dict[str, Any]] = Field(default=None, description="必须包含的参数及其值 / Required params and values")
    param_source: Optional[dict[str, str]] = Field(default=None, description="参数来源约束 / Parameter source constraints")


class ToolCallConstraints(BaseModel):
    """工具调用链约束 / Tool call chain constraints"""
    ordered: bool = Field(default=False, description="是否要求严格顺序 / Whether strict order is required")
    required_sequence: Optional[list[str]] = Field(default=None, description="必须出现的调用序列 / Required call sequence")
    forbidden_tools: Optional[list[str]] = Field(default=None, description="禁止调用的工具 / Forbidden tools")
    max_calls: Optional[int] = Field(default=None, description="最大调用次数限制 / Maximum call count limit")


# ─── 期望输出 / Expected output ──────────────────────────

class ExpectedOutput(BaseModel):
    """期望输出 / Expected output

    用户只需写 output（理想回答），框架自动从内容准确性、行为正确性、
    结构完整性三个维度用 LLM 评判。
    User only needs to write output (ideal answer), the framework automatically
    evaluates from three dimensions: content accuracy, behavioral correctness,
    and structural completeness using LLM.

    如果需要额外的精确校验（如检查关键词、校验 JSON 格式），可以补充
    下方的可选字段，框架会在 LLM 评判之外叠加这些确定性检查。
    For additional precise validations (e.g., keyword checks, JSON format),
    add the optional fields below; the framework will apply these deterministic
    checks on top of LLM evaluation.
    """

    # --- 理想回答（必填，框架自动评判的核心依据）/ Ideal answer (required, core basis for auto evaluation) ---
    output: Optional[str] = Field(default=None, description="理想的 Agent 回答 / Ideal Agent response")

    # --- 可选：额外的精确校验规则 / Optional: additional precise validation rules ---
    # 结构校验 / Structure validation
    json_schema: Optional[dict] = Field(default=None, description="JSON Schema 校验 / JSON Schema validation")
    schema_file: Optional[str] = Field(default=None, description="JSON Schema 文件路径 / JSON Schema file path")
    exact_json: Optional[dict] = Field(default=None, description="精确 JSON 匹配 / Exact JSON match")
    json_path_assertions: Optional[list[JsonPathAssertion]] = Field(default=None, description="JSONPath 校验规则 / JSONPath validation rules")

    # 行为校验 / Behavior validation
    behavior: Optional[str] = Field(default=None, description="期望行为：refuse, ask_clarification 等 / Expected behavior: refuse, ask_clarification, etc.")
    behavior_hint: Optional[str] = Field(default=None, description="行为评判提示 / Behavior evaluation hint")
    required_tool_calls: Optional[list[ToolCallAssertion]] = Field(default=None, description="必须出现的工具调用 / Required tool calls")
    tool_call_constraints: Optional[ToolCallConstraints] = Field(default=None, description="工具调用链约束 / Tool call chain constraints")

    # 内容校验 / Content validation
    contains: Optional[list[str]] = Field(default=None, description="回答中应包含的关键词 / Keywords that should appear in response")
    not_contains: Optional[list[str]] = Field(default=None, description="回答中不应包含的关键词 / Keywords that should not appear in response")
    semantic_criteria: Optional[list[str]] = Field(default=None, description="语义评判标准 / Semantic evaluation criteria")

    # 自定义校验 / Custom validation
    validator: Optional[str] = Field(default=None, description="自定义校验函数路径 / Custom validator function path")


# ─── 输入模型 / Input model ──────────────────────────────

class TestCaseInput(BaseModel):
    """测试用例输入 / Test case input"""
    query: str = Field(..., description="用户输入 / User input")
    context: Optional[dict[str, Any]] = Field(default=None, description="额外上下文 / Additional context")


# ─── 测试用例 / Test case ────────────────────────────────

class TestCase(BaseModel):
    """单个测试用例 / Single test case

    写法：给一个输入，写一个理想回答（expected_output），框架自动评判。
    Usage: provide an input, write an ideal answer (expected_output), framework auto-evaluates.
    """
    id: str = Field(..., description="用例 ID / Case ID")
    name: str = Field(..., description="用例名称 / Case name")
    input: str | TestCaseInput = Field(..., description="输入 / Input")

    # 理想回答 / Ideal answer
    expected_output: Optional[str] = Field(default=None, description="理想的 Agent 回答 / Ideal Agent response")
    # 内部使用（expected_output 会自动同步到 expected.output）/ Internal use (expected_output auto-syncs to expected.output)
    expected: ExpectedOutput = Field(default_factory=ExpectedOutput, description="期望输出详情 / Expected output details")

    tags: list[str] = Field(default_factory=list, description="标签 / Tags")
    judge_hints: Optional[str] = Field(default=None, description="给评判器的额外提示 / Additional hints for the judge")

    # --- 新增字段（均有默认值，向后兼容）/ New fields (all with defaults, backward compatible) ---
    source: TestCaseSource = Field(default=TestCaseSource.MANUAL, description="用例来源 / Case source")
    parent_id: Optional[str] = Field(default=None, description="变异来源用例 ID / Parent case ID for mutation")
    mutation_strategy: Optional[str] = Field(default=None, description="LLM 选择的变异方式（自由文本）/ LLM-chosen mutation strategy (free text)")
    review_status: ReviewStatus = Field(default=ReviewStatus.APPROVED, description="审核状态 / Review status")
    tier: TestCaseTier = Field(default=TestCaseTier.GOLD, description="评测集层级 / Test set tier")
    bad_output: Optional[str] = Field(default=None, description="错误输出（线上采集的 Agent 原始错误回复）/ Bad output (original wrong response from production)")

    @model_validator(mode="after")
    def sync_expected_output(self) -> "TestCase":
        """将顶级 expected_output 同步到 expected.output / Sync top-level expected_output to expected.output"""
        if self.expected_output and not self.expected.output:
            self.expected.output = self.expected_output
        elif self.expected.output and not self.expected_output:
            self.expected_output = self.expected.output
        return self

    @property
    def input_query(self) -> str:
        """获取输入查询字符串 / Get input query string"""
        if isinstance(self.input, str):
            return self.input
        return self.input.query

    @property
    def input_context(self) -> Optional[dict[str, Any]]:
        """获取输入上下文 / Get input context"""
        if isinstance(self.input, str):
            return None
        return self.input.context


# ─── 测试套件 / Test suite ───────────────────────────────

class TestSuite(BaseModel):
    """测试套件 / Test suite"""
    name: str = Field(..., description="套件名称 / Suite name")
    description: Optional[str] = Field(default=None)
    context: Optional[dict[str, Any]] = Field(default=None, description="全局上下文 / Global context")
    cases: list[TestCase] = Field(..., description="测试用例列表 / Test case list")
    tier: Optional[TestCaseTier] = Field(default=None, description="套件级别的默认层级 / Suite-level default tier")
