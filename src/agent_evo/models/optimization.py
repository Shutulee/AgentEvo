"""优化结果模型"""

from typing import Optional
from pydantic import BaseModel, Field


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
