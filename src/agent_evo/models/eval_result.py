"""评测结果模型"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    """用例状态"""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


# ─── 因子评分 ────────────────────────────────────────────

class FactorResult(BaseModel):
    """单因子评测结果"""
    factor_id: str                             # structure / behavior / content / custom
    score: float = Field(ge=0.0, le=1.0)       # 0.0 - 1.0
    reason: str = ""                           # 评分理由（即该维度的归因）
    details: dict[str, Any] = Field(default_factory=dict)  # 详细信息


class FactorSummary(BaseModel):
    """单个因子的全局统计"""
    factor_id: str
    activated_count: int = 0       # 激活次数
    avg_score: float = 0.0         # 平均分
    fail_count: int = 0            # 不通过次数
    fatal_fail_count: int = 0      # 致命失败次数


# ─── 用例结果 ────────────────────────────────────────────

class CaseResult(BaseModel):
    """单个用例评测结果"""
    case_id: str
    case_name: str
    status: CaseStatus

    # 输入输出
    input: str
    output: str
    expected: dict[str, Any]

    # 因子评分
    factor_scores: list[FactorResult] = Field(default_factory=list)
    weighted_score: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = Field(default=0.0, ge=0.0, le=1.0)

    # 判定
    passed: bool = False
    fail_reason: Optional[str] = None

    # 评判摘要
    summary: str = ""

    # 元数据
    tags: list[str] = Field(default_factory=list)
    execution_time_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None


# ─── 统计 ────────────────────────────────────────────────

class TagStats(BaseModel):
    """按 tag 统计"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    # 新增
    threshold: Optional[float] = None       # 该 tag 配置的通过阈值
    meets_threshold: Optional[bool] = None  # 是否达标


# ─── 聚合归因 ────────────────────────────────────────────

class AggregatedDiagnosis(BaseModel):
    """聚合归因 — 全局模式分析"""
    common_patterns: list[str] = Field(default_factory=list)
    issues_by_tag: dict[str, list[str]] = Field(default_factory=dict)
    fix_priorities: list[str] = Field(default_factory=list)
    suggested_prompt_changes: list[str] = Field(default_factory=list)
    auto_fixable_ratio: float = 0.0


# ─── 评测报告 ────────────────────────────────────────────

class EvalReport(BaseModel):
    """评测报告"""
    # 概览
    total: int = 0
    passed: int = 0
    failed: int = 0
    error: int = 0
    skipped: int = 0
    pass_rate: float = 0.0

    # 详细结果
    results: list[CaseResult] = Field(default_factory=list)

    # 按 tag 统计
    stats_by_tag: dict[str, TagStats] = Field(default_factory=dict)

    # 因子维度统计
    factor_summary: dict[str, FactorSummary] = Field(default_factory=dict)

    # 门禁判断
    release_blocked: bool = False
    blocking_tags: list[str] = Field(default_factory=list)

    # 失败汇总（按 tag 分类）
    failures_by_tag: dict[str, list[str]] = Field(default_factory=dict)  # tag -> [case_id]

    # 归因汇总
    aggregated_diagnosis: Optional[AggregatedDiagnosis] = None

    # 优化结果
    optimization: Optional["OptimizationResult"] = None

    # 时间
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    def get_failed_results(self) -> list[CaseResult]:
        """获取失败的用例"""
        return [r for r in self.results if r.status == CaseStatus.FAILED]


# 避免循环引用
from agent_evo.models.optimization import OptimizationResult  # noqa: E402
EvalReport.model_rebuild()
