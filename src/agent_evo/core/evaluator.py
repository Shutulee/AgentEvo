"""LLM-as-Judge 评判器"""

import json
from pathlib import Path
from typing import Optional

from agent_evo.models import (
    Config, CaseResult, CaseStatus, EvalReport, DimensionScore,
    DiagnosisResult, DiagnosisCategory
)
from agent_evo.core.generator import GeneratorResult
from agent_evo.utils.llm import LLMClient


class Evaluator:
    """LLM-as-Judge 评判器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config.llm)
        self.judge_prompt = self._load_prompt("judge")
        self.diagnose_prompt = self._load_prompt("diagnose")
    
    def _load_prompt(self, name: str) -> str:
        """加载内置提示词"""
        prompt_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompt_dir / f"{name}.md"
        
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        
        # 返回默认提示词
        return self._get_default_prompt(name)
    
    def _get_default_prompt(self, name: str) -> str:
        """获取默认提示词"""
        if name == "judge":
            return """你是一个 AI 输出质量评判专家。请评判以下 Agent 输出。

## 输入
用户输入: {input}

## 期望
{expected}

## 实际输出
{output}

## 评分维度
{dimensions}

请以 JSON 格式输出：
{{
  "score": 0.0-1.0,
  "passed": true/false,
  "dimensions": [{{"name": "...", "score": 0.0-1.0, "reason": "..."}}],
  "summary": "整体评价"
}}"""
        elif name == "diagnose":
            return """你是一个 LLM Agent 调试专家。请分析失败原因。

## 失败用例
- 输入: {input}
- 期望: {expected}
- 实际: {output}

## 当前系统提示词
{prompt_content}

## 归因类别
- PROMPT_ISSUE: 提示词缺陷（可自动修复）
- CONTEXT_ISSUE: 上下文/知识不足
- EDGE_CASE: 边界场景（可自动修复）

请以 JSON 格式输出：
{{
  "category": "PROMPT_ISSUE|CONTEXT_ISSUE|EDGE_CASE",
  "confidence": 0.0-1.0,
  "root_cause": "根本原因",
  "suggestion": "修复建议",
  "auto_fixable": true/false
}}"""
        return ""
    
    async def evaluate_case(self, result: GeneratorResult) -> CaseResult:
        """评判单个用例"""
        case = result.case
        
        # 如果执行出错，直接返回错误状态
        if result.error:
            return CaseResult(
                case_id=case.id,
                case_name=case.name,
                status=CaseStatus.ERROR,
                input=case.input_query,
                output=result.output,
                expected=case.expected.model_dump(),
                score=0.0,
                summary=f"执行错误: {result.error}",
                execution_time_ms=result.execution_time_ms,
                error_message=result.error
            )
        
        # 构建评判 prompt
        dimensions_str = "\n".join([
            f"- {d.name} (权重 {d.weight}): {d.description}"
            for d in self.config.judge.dimensions
        ])
        
        prompt = self.judge_prompt.format(
            input=case.input_query,
            expected=json.dumps(case.expected.model_dump(), ensure_ascii=False, indent=2),
            output=result.output,
            dimensions=dimensions_str
        )
        
        # 调用 LLM 评判
        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            judge_result = json.loads(response)
            
            # 解析维度评分
            dimension_scores = [
                DimensionScore(
                    name=d["name"],
                    score=d["score"],
                    reason=d.get("reason", "")
                )
                for d in judge_result.get("dimensions", [])
            ]
            
            score = judge_result.get("score", 0.0)
            passed = score >= self.config.judge.pass_threshold
            
            return CaseResult(
                case_id=case.id,
                case_name=case.name,
                status=CaseStatus.PASSED if passed else CaseStatus.FAILED,
                input=case.input_query,
                output=result.output,
                expected=case.expected.model_dump(),
                score=score,
                dimension_scores=dimension_scores,
                summary=judge_result.get("summary", ""),
                execution_time_ms=result.execution_time_ms
            )
        except Exception as e:
            return CaseResult(
                case_id=case.id,
                case_name=case.name,
                status=CaseStatus.ERROR,
                input=case.input_query,
                output=result.output,
                expected=case.expected.model_dump(),
                score=0.0,
                summary=f"评判错误: {e}",
                execution_time_ms=result.execution_time_ms,
                error_message=str(e)
            )
    
    async def evaluate_all(self, results: list[GeneratorResult]) -> EvalReport:
        """评判所有用例"""
        case_results = []
        
        for result in results:
            case_result = await self.evaluate_case(result)
            case_results.append(case_result)
        
        # 统计
        total = len(case_results)
        passed = sum(1 for r in case_results if r.status == CaseStatus.PASSED)
        failed = sum(1 for r in case_results if r.status == CaseStatus.FAILED)
        error = sum(1 for r in case_results if r.status == CaseStatus.ERROR)
        
        return EvalReport(
            total=total,
            passed=passed,
            failed=failed,
            error=error,
            pass_rate=passed / total if total > 0 else 0.0,
            results=case_results
        )
    
    async def diagnose_case(
        self,
        case_result: CaseResult,
        prompt_content: str
    ) -> DiagnosisResult:
        """诊断单个失败用例"""
        prompt = self.diagnose_prompt.format(
            input=case_result.input,
            expected=json.dumps(case_result.expected, ensure_ascii=False, indent=2),
            output=case_result.output,
            prompt_content=prompt_content
        )
        
        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
            return DiagnosisResult(
                case_id=case_result.case_id,
                category=DiagnosisCategory(result.get("category", "PROMPT_ISSUE")),
                confidence=result.get("confidence", 0.5),
                root_cause=result.get("root_cause", "未知"),
                suggestion=result.get("suggestion", ""),
                auto_fixable=result.get("auto_fixable", False)
            )
        except Exception as e:
            return DiagnosisResult(
                case_id=case_result.case_id,
                category=DiagnosisCategory.PROMPT_ISSUE,
                confidence=0.0,
                root_cause=f"诊断错误: {e}",
                suggestion="",
                auto_fixable=False
            )
    
    async def diagnose_all(self, failed_results: list[CaseResult]) -> list[DiagnosisResult]:
        """诊断所有失败用例"""
        # 读取当前提示词
        prompt_file = Path(self.config.agent.prompt_file)
        if prompt_file.exists():
            prompt_content = prompt_file.read_text(encoding="utf-8")
        else:
            prompt_content = "(提示词文件不存在)"
        
        diagnoses = []
        for result in failed_results:
            diagnosis = await self.diagnose_case(result, prompt_content)
            diagnoses.append(diagnosis)
        
        return diagnoses
