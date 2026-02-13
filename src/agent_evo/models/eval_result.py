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


class DimensionScore(BaseModel):
    """维度评分"""
    name: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class CaseResult(BaseModel):
    """单个用例评测结果"""
    case_id: str
    case_name: str
    status: CaseStatus
    
    # 输入输出
    input: str
    output: str
    expected: dict[str, Any]
    
    # 评分
    score: float = Field(ge=0.0, le=1.0)
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    
    # 评判摘要
    summary: str = ""
    
    # 诊断结果（失败时填充）
    diagnosis: Optional["DiagnosisResult"] = None
    
    # 元数据
    execution_time_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None


class TagStats(BaseModel):
    """按 tag 统计"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0


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
    
    # 时间
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    def get_failed_results(self) -> list[CaseResult]:
        """获取失败的用例"""
        return [r for r in self.results if r.status == CaseStatus.FAILED]


# 避免循环引用
from agent_evo.models.diagnosis import DiagnosisResult
CaseResult.model_rebuild()
