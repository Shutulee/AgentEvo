"""配置模型"""

from typing import Optional
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """被测 Agent 配置"""
    module: str = Field(..., description="Agent 入口模块")
    function: str = Field(default="run", description="Agent 入口函数")
    prompt_file: str = Field(..., description="系统提示词文件路径")


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = Field(default="openai", description="LLM 提供商")
    model: str = Field(default="gpt-4o", description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API Key，支持 ${ENV_VAR} 格式")
    base_url: Optional[str] = Field(default=None, description="API Base URL")


class DimensionConfig(BaseModel):
    """评分维度配置"""
    name: str
    weight: float = 1.0
    description: str = ""


class JudgeConfig(BaseModel):
    """评判配置"""
    pass_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="通过阈值")
    dimensions: list[DimensionConfig] = Field(
        default_factory=lambda: [
            DimensionConfig(name="correctness", weight=0.5, description="输出正确性"),
            DimensionConfig(name="completeness", weight=0.3, description="输出完整性"),
            DimensionConfig(name="format", weight=0.2, description="格式规范性"),
        ]
    )


class CategoryConfig(BaseModel):
    """归因类别配置"""
    id: str
    description: str
    auto_fix: bool = False


class DiagnosisConfig(BaseModel):
    """诊断配置"""
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度阈值")
    categories: list[CategoryConfig] = Field(
        default_factory=lambda: [
            CategoryConfig(id="PROMPT_ISSUE", description="提示词缺陷", auto_fix=True),
            CategoryConfig(id="CONTEXT_ISSUE", description="上下文/知识不足", auto_fix=False),
            CategoryConfig(id="EDGE_CASE", description="边界场景", auto_fix=True),
        ]
    )


class OptimizationConfig(BaseModel):
    """优化配置"""
    max_iterations: int = Field(default=3, ge=1, description="最大迭代次数")
    run_regression: bool = Field(default=True, description="优化后是否运行回归测试")
    regression_threshold: float = Field(default=0.95, ge=0.0, le=1.0, description="回归测试通过率阈值")


class GitConfig(BaseModel):
    """Git 集成配置"""
    enabled: bool = Field(default=True)
    auto_commit: bool = Field(default=False)
    create_pr: bool = Field(default=True)
    pr_base_branch: str = Field(default="main")
    pr_branch_prefix: str = Field(default="agent-evo/optimize")


class Config(BaseModel):
    """AgentEvo 完整配置"""
    version: str = "1"
    agent: AgentConfig
    test_cases: str = Field(default="./tests/*.yaml", description="测试用例路径，支持 glob")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    diagnosis: DiagnosisConfig = Field(default_factory=DiagnosisConfig)
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    git: GitConfig = Field(default_factory=GitConfig)
