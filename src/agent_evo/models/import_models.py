"""导入数据模型 / Import data models"""

from datetime import datetime
from typing import Optional, Any, Literal
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


# ─── HTTP 数据源配置 / HTTP data source configuration ─────

class APISourceConfig(BaseModel):
    """HTTP API 数据源配置 / HTTP API data source configuration

    用于声明式地配置线上数据拉取。支持 ${ENV_VAR} 环境变量引用。
    Declaratively configure production data fetching. Supports ${ENV_VAR} references.
    """
    name: str = Field(default="default", description="数据源名称（用于 --source 引用）/ Source name (for --source reference)")
    type: Literal["api"] = Field(default="api", description="数据源类型 / Source type")
    url: str = Field(..., description="API 地址 / API URL")
    method: Literal["GET", "POST"] = Field(default="GET", description="HTTP 方法 / HTTP method")
    headers: dict[str, str] = Field(default_factory=dict, description="请求头 / Request headers")
    params: dict[str, Any] = Field(default_factory=dict, description="查询参数（GET）或请求体（POST）/ Query params (GET) or request body (POST)")
    # 分页配置 / Pagination configuration
    pagination: Optional["PaginationConfig"] = Field(default=None, description="分页配置 / Pagination config")
    # 响应解析 / Response parsing
    data_path: str = Field(default="data", description="JSON 响应中数据数组的路径（点分隔，如 data.records）/ Path to data array in JSON response (dot-separated, e.g. data.records)")
    # 字段映射：API 字段名 → AgentEvo 标准字段名 / Field mapping: API field name → AgentEvo standard field name
    field_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "query": "query",
            "agent_response": "agent_response",
        },
        description="字段映射 / Field mapping: AgentEvo field → API field",
    )
    # 可选过滤 / Optional filter
    filter: Optional[dict[str, Any]] = Field(default=None, description="请求时附加的过滤条件 / Additional filter conditions for request")
    # 超时 / Timeout
    timeout: int = Field(default=30, description="请求超时秒数 / Request timeout in seconds")


class PaginationConfig(BaseModel):
    """分页配置 / Pagination configuration"""
    type: Literal["page", "cursor", "offset"] = Field(default="page", description="分页类型 / Pagination type")
    page_param: str = Field(default="page", description="页码参数名 / Page number param name")
    size_param: str = Field(default="page_size", description="每页大小参数名 / Page size param name")
    size: int = Field(default=100, description="每页大小 / Page size")
    total_path: Optional[str] = Field(default=None, description="响应中总数字段路径 / Path to total count in response")
    cursor_path: Optional[str] = Field(default=None, description="响应中游标字段路径 / Path to cursor in response")
    cursor_param: Optional[str] = Field(default=None, description="请求中游标参数名 / Cursor param name in request")
    max_pages: int = Field(default=100, description="最大拉取页数（安全阀）/ Maximum pages to fetch (safety limit)")
