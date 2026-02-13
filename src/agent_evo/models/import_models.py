"""导入数据模型 / Import data models"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class ProductionRecord(BaseModel):
    """线上生产数据记录 / Production data record"""
    query: str = Field(..., description="用户原始输入 / User original input")
    agent_response: str = Field(..., description="Agent 原始回复 / Agent original response")
    is_correct: Optional[bool] = Field(default=None, description="人工标注：是否正确 / Manual label: is correct")
    corrected_response: Optional[str] = Field(default=None, description="纠错后的期望回复 / Corrected expected response")
    error_type: Optional[str] = Field(default=None, description="错误类型标注 / Error type label")
    source_timestamp: Optional[datetime] = Field(default=None, description="原始时间戳 / Original timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据 / Additional metadata")


class ImportResult(BaseModel):
    """导入结果 / Import result"""
    total_records: int = 0
    imported: int = 0
    duplicates_removed: int = 0
    pending_review: int = 0
    errors: list[str] = Field(default_factory=list)
