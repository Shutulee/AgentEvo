"""配置模型 / Configuration models"""

import warnings
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator


class AgentConfig(BaseModel):
    """被测 Agent 配置 / Agent under test configuration"""
    module: str = Field(..., description="Agent 入口模块 / Agent entry module")
    function: str = Field(default="run", description="Agent 入口函数 / Agent entry function")
    prompt_file: str = Field(..., description="系统提示词文件路径 / System prompt file path")


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
    test_cases: str = Field(default="./tests/*.yaml", description="测试用例路径，支持 glob / Test cases path, supports glob")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    git: GitConfig = Field(default_factory=GitConfig)

    # 新增配置节（均可选，不配不影响现有功能）
    # Additional config sections (all optional, no impact on existing features)
    mutation: MutationConfig = Field(default_factory=MutationConfig)
    import_config: Optional[ImportConfig] = Field(default=None, alias="import")
    tag_policies: dict[str, TagPolicyConfig] = Field(default_factory=dict)

    # 报告语言配置：zh=中文, en=English
    # Report language setting: zh=Chinese, en=English
    language: Literal["zh", "en"] = Field(default="zh", description="报告输出语言 / Report output language: zh or en")

    model_config = {"populate_by_name": True}
