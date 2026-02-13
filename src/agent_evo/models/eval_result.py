"""评测结果模型 / Evaluation result models"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    """用例状态 / Case status"""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


# ─── 因子评分 / Factor scoring ────────────────────────────

class FactorResult(BaseModel):
    """单因子评测结果 / Single factor evaluation result"""
    factor_id: str                             # 因子 ID / Factor ID: structure / behavior / content / custom
    score: float = Field(ge=0.0, le=1.0)       # 评分 0.0 - 1.0 / Score 0.0 - 1.0
    reason: str = ""                           # 评分理由（即该维度的归因）/ Scoring reason (attribution for this dimension)
    details: dict[str, Any] = Field(default_factory=dict)  # 详细信息 / Detailed info


class FactorSummary(BaseModel):
    """单个因子的全局统计 / Global statistics for a single factor"""
    factor_id: str
    activated_count: int = 0       # 激活次数 / Activation count
    avg_score: float = 0.0         # 平均分 / Average score
    fail_count: int = 0            # 不通过次数 / Failure count
    fatal_fail_count: int = 0      # 致命失败次数 / Fatal failure count


# ─── 用例结果 / Case results ─────────────────────────────

class CaseResult(BaseModel):
    """单个用例评测结果 / Single case evaluation result"""
    case_id: str
    case_name: str
    status: CaseStatus

    # 输入输出 / Input and output
    input: str
    output: str
    expected: dict[str, Any]

    # 因子评分 / Factor scores
    factor_scores: list[FactorResult] = Field(default_factory=list)
    weighted_score: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = Field(default=0.0, ge=0.0, le=1.0)

    # 判定 / Judgment
    passed: bool = False
    fail_reason: Optional[str] = None

    # 评判摘要 / Judgment summary
    summary: str = ""

    # 元数据 / Metadata
    tags: list[str] = Field(default_factory=list)
    execution_time_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None


# ─── 统计 / Statistics ───────────────────────────────────

class TagStats(BaseModel):
    """按 tag 统计 / Statistics by tag"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    # 新增 / Additional fields
    threshold: Optional[float] = None       # 该 tag 配置的通过阈值 / Pass threshold configured for this tag
    meets_threshold: Optional[bool] = None  # 是否达标 / Whether the threshold is met


# ─── 聚合归因 / Aggregated diagnosis ─────────────────────

class AggregatedDiagnosis(BaseModel):
    """聚合归因 — 全局模式分析 / Aggregated diagnosis — global pattern analysis"""
    common_patterns: list[str] = Field(default_factory=list)
    issues_by_tag: dict[str, list[str]] = Field(default_factory=dict)
    fix_priorities: list[str] = Field(default_factory=list)
    suggested_prompt_changes: list[str] = Field(default_factory=list)
    auto_fixable_ratio: float = 0.0


# ─── 评测报告 / Evaluation report ────────────────────────

class EvalReport(BaseModel):
    """评测报告 / Evaluation report"""
    # 概览 / Overview
    total: int = 0
    passed: int = 0
    failed: int = 0
    error: int = 0
    skipped: int = 0
    pass_rate: float = 0.0

    # 详细结果 / Detailed results
    results: list[CaseResult] = Field(default_factory=list)

    # 按 tag 统计 / Statistics by tag
    stats_by_tag: dict[str, TagStats] = Field(default_factory=dict)

    # 因子维度统计 / Factor dimension statistics
    factor_summary: dict[str, FactorSummary] = Field(default_factory=dict)

    # 门禁判断 / Gate check
    release_blocked: bool = False
    blocking_tags: list[str] = Field(default_factory=list)

    # 失败汇总（按 tag 分类）/ Failures summary (grouped by tag)
    failures_by_tag: dict[str, list[str]] = Field(default_factory=dict)  # tag -> [case_id]

    # 归因汇总 / Diagnosis summary
    aggregated_diagnosis: Optional[AggregatedDiagnosis] = None

    # 优化结果 / Optimization result
    optimization: Optional["OptimizationResult"] = None

    # 时间 / Timing
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    def get_failed_results(self) -> list[CaseResult]:
        """获取失败的用例 / Get failed cases"""
        return [r for r in self.results if r.status == CaseStatus.FAILED]


# 避免循环引用 / Avoid circular imports
from agent_evo.models.optimization import OptimizationResult  # noqa: E402
EvalReport.model_rebuild()
