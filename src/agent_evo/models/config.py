"""配置模型 / Configuration models"""

import warnings
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator

from agent_evo.models.import_models import APISourceConfig


class HttpAgentConfig(BaseModel):
    """HTTP Agent 配置 / HTTP Agent configuration"""
    url: str = Field(..., description="API 地址 / API URL")
    method: str = Field(default="POST", description="HTTP 方法 / HTTP method")
    headers: dict[str, str] = Field(default_factory=dict, description="请求头 / Request headers")
    body: dict = Field(
        default_factory=lambda: {"input": "${input}"},
        description="请求体模板，${input} 会被替换为测试输入 / Request body template, ${input} is replaced",
    )
    response_path: Optional[str] = Field(
        default=None,
        description="非流式响应中结果的 JSON 路径 / JSON path for result in non-streaming response",
    )
    stream: bool = Field(default=False, description="是否为 SSE 流式接口 / Whether SSE streaming")
    stream_event_field: str = Field(default="event", description="SSE 事件类型字段名 / SSE event type field")
    stream_content_field: str = Field(default="content", description="SSE 内容字段名 / SSE content field")
    stream_done_event: str = Field(default="done", description="SSE 完成事件名 / SSE done event name")
    stream_text_events: list[str] = Field(
        default_factory=lambda: ["text"],
        description="视为文本输出的事件类型 / Event types treated as text output",
    )
    timeout: float = Field(default=120.0, description="请求超时秒数 / Request timeout in seconds")


class AgentConfig(BaseModel):
    """被测 Agent 配置 / Agent under test configuration

    支持两种模式 / Supports two modes:
    - callable: 本地 Python 函数调用（默认）/ Local Python function call (default)
    - http: 远程 HTTP API 调用 / Remote HTTP API call
    """
    type: Literal["callable", "http"] = Field(
        default="callable",
        description="适配器类型 / Adapter type: callable (local function) or http (remote API)",
    )

    # callable 模式字段（type=callable 时必填）
    # callable mode fields (required when type=callable)
    module: Optional[str] = Field(default=None, description="Agent 入口模块 / Agent entry module")
    function: str = Field(default="run", description="Agent 入口函数 / Agent entry function")

    # 通用字段 / Common fields
    prompt_file: Optional[str] = Field(default=None, description="系统提示词文件路径 / System prompt file path")

    # http 模式字段（type=http 时必填）
    # http mode fields (required when type=http)
    http: Optional[HttpAgentConfig] = Field(default=None, description="HTTP 适配器配置 / HTTP adapter config")

    @model_validator(mode="after")
    def validate_agent_config(self) -> "AgentConfig":
        """根据 type 验证必填字段 / Validate required fields based on type"""
        if self.type == "callable":
            if not self.module:
                raise ValueError("agent.module is required when type is 'callable'")
            if not self.prompt_file:
                raise ValueError("agent.prompt_file is required when type is 'callable'")
        elif self.type == "http":
            if not self.http:
                raise ValueError("agent.http is required when type is 'http'")
        return self


class LLMConfig(BaseModel):
    """LLM 配置 / LLM configuration"""
    provider: str = Field(default="openai", description="LLM 提供商 / LLM provider")
    model: str = Field(default="gpt-4o", description="模型名称 / Model name")
    api_key: Optional[str] = Field(default=None, description="API Key，支持 ${ENV_VAR} 格式 / API Key, supports ${ENV_VAR}")
    base_url: Optional[str] = Field(default=None, description="API Base URL")


# ─── Deprecated ──────────────────────────────────────────

class DimensionConfig(BaseModel):
    """评分维度配置（已废弃，保留向后兼容）/ Scoring dimension config (deprecated, kept for backward compat)"""
    name: str
    weight: float = 1.0
    description: str = ""


# ─── 新增配置 / Additional configuration ─────────────────

class FactorConfig(BaseModel):
    """因子配置 / Factor configuration"""
    weight: float = Field(default=1.0, ge=0.0, description="因子权重 / Factor weight")
    fatal: bool = Field(default=False, description="致命因子：不通过则整条用例失败 / Fatal factor: case fails if not passed")


class TagPolicyConfig(BaseModel):
    """基于 tag 的评测策略 / Tag-based evaluation policy"""
    pass_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    fail_fast: bool = Field(default=False, description="一条失败即停止 / Stop on first failure")
    required_for_release: bool = Field(default=False, description="发布阻断 / Required for release")
    description: str = ""


class MutationConfig(BaseModel):
    """变异扩充配置 / Mutation expansion configuration"""
    count_per_case: int = Field(default=3, ge=1)
    auto_review: bool = Field(default=True, description="是否使用 LLM 预审 / Whether to use LLM pre-review")
    business_docs: Optional[str] = Field(default=None, description="业务文档路径 / Business document path")
    hint_directions: list[str] = Field(default_factory=list, description="参考方向提示 / Reference direction hints")


class ImportConfig(BaseModel):
    """导入配置 / Import configuration"""
    default_format: str = "jsonl"
    auto_refine: bool = True
    auto_deduplicate: bool = True
    default_tier: str = "silver"
    default_tags: list[str] = Field(default_factory=lambda: ["regression"])


# ─── 主配置 / Main configuration ─────────────────────────

class JudgeConfig(BaseModel):
    """评判配置 / Judge configuration"""
    pass_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="通过阈值 / Pass threshold")

    # 因子权重 / Factor weights
    factors: dict[str, FactorConfig] = Field(
        default_factory=lambda: {
            "content": FactorConfig(weight=1.0, fatal=False),
            "behavior": FactorConfig(weight=0.8, fatal=False),
            "structure": FactorConfig(weight=0.5, fatal=False),
            "custom": FactorConfig(weight=1.0, fatal=True),
        }
    )

    # 已废弃：旧 dimensions 格式，保留向后兼容 / Deprecated: old dimensions format, kept for backward compat
    dimensions: Optional[list[DimensionConfig]] = Field(default=None)

    @model_validator(mode="after")
    def migrate_dimensions_to_factors(self) -> "JudgeConfig":
        """如果用户配置了旧的 dimensions，自动映射为 content 因子并打 warning
        If user configured old dimensions, auto-map to content factor with a warning"""
        if self.dimensions is not None:
            warnings.warn(
                "judge.dimensions 已废弃，请迁移到 judge.factors 格式。"
                "旧的 dimensions 已自动映射为 content 因子。"
                " / judge.dimensions is deprecated, migrate to judge.factors."
                " Old dimensions auto-mapped to content factor.",
                DeprecationWarning,
                stacklevel=2,
            )
            # 旧 dimensions 的加权总权重映射到 content 因子 / Map old dimensions total weight to content factor
            total_weight = sum(d.weight for d in self.dimensions)
            if total_weight > 0:
                self.factors["content"] = FactorConfig(weight=total_weight, fatal=False)
        return self


class OptimizationConfig(BaseModel):
    """优化配置 / Optimization configuration"""
    max_iterations: int = Field(default=3, ge=1, description="最大迭代次数 / Maximum iterations")
    run_regression: bool = Field(default=True, description="优化后是否运行回归测试 / Run regression tests after optimization")
    regression_threshold: float = Field(default=0.95, ge=0.0, le=1.0, description="回归测试通过率阈值 / Regression pass rate threshold")


class GitConfig(BaseModel):
    """Git 集成配置 / Git integration configuration"""
    enabled: bool = Field(default=True)
    auto_commit: bool = Field(default=False)
    create_pr: bool = Field(default=True)
    pr_base_branch: str = Field(default="main")
    pr_branch_prefix: str = Field(default="agent-evo/optimize")


class Config(BaseModel):
    """AgentEvo 完整配置 / AgentEvo full configuration"""
    version: str = "1"
    agent: AgentConfig
    test_cases: str = Field(default="./tests/gold/**/*.yaml", description="黄金测评集路径（glob）/ Gold test cases path (glob)")
    silver_test_cases: str = Field(default="./tests/silver/**/*.yaml", description="白银测评集路径（glob）/ Silver test cases path (glob)")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    git: GitConfig = Field(default_factory=GitConfig)

    # 新增配置节（均可选，不配不影响现有功能）
    # Additional config sections (all optional, no impact on existing features)
    mutation: MutationConfig = Field(default_factory=MutationConfig)
    import_config: Optional[ImportConfig] = Field(default=None, alias="import")
    tag_policies: dict[str, TagPolicyConfig] = Field(default_factory=dict)

    # HTTP 数据源配置（用于 agent-evo import --source）
    # HTTP data source config (for agent-evo import --source)
    import_sources: list[APISourceConfig] = Field(default_factory=list)

    # 报告语言配置：zh=中文, en=English
    # Report language setting: zh=Chinese, en=English
    language: Literal["zh", "en"] = Field(default="zh", description="报告输出语言 / Report output language: zh or en")

    model_config = {"populate_by_name": True}
