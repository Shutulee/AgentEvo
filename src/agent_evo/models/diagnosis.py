"""诊断结果模型"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DiagnosisCategory(str, Enum):
    """诊断归因类别"""
    PROMPT_ISSUE = "PROMPT_ISSUE"
    CONTEXT_ISSUE = "CONTEXT_ISSUE"
    EDGE_CASE = "EDGE_CASE"
    TOOL_ISSUE = "TOOL_ISSUE"
    MODEL_LIMITATION = "MODEL_LIMITATION"


class DiagnosisResult(BaseModel):
    """诊断结果"""
    case_id: str
    
    # 归因
    category: DiagnosisCategory
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")
    
    # 分析
    root_cause: str = Field(..., description="根本原因")
    evidence: list[str] = Field(default_factory=list, description="证据")
    
    # 建议
    suggestion: str = Field(..., description="修复建议")
    
    # 是否可自动修复
    auto_fixable: bool = False
    
    # 修复 diff（如果可修复）
    fix_diff: Optional[str] = None


class OptimizationResult(BaseModel):
    """优化结果"""
    success: bool = False
    iterations: int = 0
    
    # 提示词变更
    original_prompt: Optional[str] = None
    optimized_prompt: Optional[str] = None
    diff: Optional[str] = None
    
    # 修复的用例
    fixed_cases: list[str] = Field(default_factory=list)
    
    # 回归测试结果
    regression_pass_rate: Optional[float] = None
    
    # 错误信息
    error_message: Optional[str] = None
