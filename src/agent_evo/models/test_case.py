"""测试用例模型"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class ExpectedOutput(BaseModel):
    """期望输出"""
    contains: Optional[list[str]] = Field(default=None, description="应包含的关键词")
    not_contains: Optional[list[str]] = Field(default=None, description="不应包含的关键词")
    schema_file: Optional[str] = Field(default=None, description="JSON Schema 文件路径")
    behavior: Optional[str] = Field(default=None, description="期望行为：refuse, ask_clarification 等")
    behavior_hint: Optional[str] = Field(default=None, description="行为评判提示")
    validator: Optional[str] = Field(default=None, description="自定义校验函数路径")


class TestCaseInput(BaseModel):
    """测试用例输入"""
    query: str = Field(..., description="用户输入")
    context: Optional[dict[str, Any]] = Field(default=None, description="额外上下文")


class TestCase(BaseModel):
    """单个测试用例"""
    id: str = Field(..., description="用例 ID")
    name: str = Field(..., description="用例名称")
    input: str | TestCaseInput = Field(..., description="输入")
    expected: ExpectedOutput = Field(..., description="期望输出")
    tags: list[str] = Field(default_factory=list, description="标签")
    judge_hints: Optional[str] = Field(default=None, description="给评判器的额外提示")
    
    @property
    def input_query(self) -> str:
        """获取输入查询字符串"""
        if isinstance(self.input, str):
            return self.input
        return self.input.query
    
    @property
    def input_context(self) -> Optional[dict[str, Any]]:
        """获取输入上下文"""
        if isinstance(self.input, str):
            return None
        return self.input.context


class TestSuite(BaseModel):
    """测试套件"""
    name: str = Field(..., description="套件名称")
    description: Optional[str] = Field(default=None)
    context: Optional[dict[str, Any]] = Field(default=None, description="全局上下文")
    cases: list[TestCase] = Field(..., description="测试用例列表")
