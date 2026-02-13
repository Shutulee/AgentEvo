"""优化结果模型 / Optimization result model"""

from typing import Optional
from pydantic import BaseModel, Field


class OptimizationResult(BaseModel):
    """优化结果 / Optimization result"""
    success: bool = False
    iterations: int = 0
    
    # 提示词变更 / Prompt changes
    original_prompt: Optional[str] = None
    optimized_prompt: Optional[str] = None
    diff: Optional[str] = None
    
    # 修复的用例 / Fixed cases
    fixed_cases: list[str] = Field(default_factory=list)
    
    # 回归测试结果 / Regression test results
    regression_pass_rate: Optional[float] = None
    
    # 错误信息 / Error message
    error_message: Optional[str] = None
