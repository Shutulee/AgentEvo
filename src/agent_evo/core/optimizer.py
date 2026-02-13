"""提示词优化器"""

import json
import re
from pathlib import Path
from typing import Optional

from agent_evo.models import Config, TestCase, DiagnosisResult, OptimizationResult
from agent_evo.utils.llm import LLMClient


class Optimizer:
    """提示词优化器"""
    
    def __init__(self, config: Config, project_dir: Path):
        self.config = config
        self.project_dir = project_dir
        self.llm = LLMClient(config.llm)
        self.optimize_prompt = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """加载优化提示词"""
        prompt_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompt_dir / "optimize.md"
        
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        
        return """你是一个 Prompt 工程专家。请根据诊断结果优化系统提示词。

## 当前提示词
{current_prompt}

## 诊断结果
{diagnoses}

## 要求
1. 保守修改，只修复必要部分
2. 保持原有风格和结构
3. 避免过拟合单个用例
4. 添加的指令要通用化

请直接输出优化后的完整提示词，用 <optimized_prompt> 和 </optimized_prompt> 标签包裹。"""
    
    async def optimize(
        self,
        diagnoses: list[DiagnosisResult],
        test_cases: list[TestCase]
    ) -> OptimizationResult:
        """
        根据诊断结果优化提示词
        
        Args:
            diagnoses: 诊断结果列表
            test_cases: 所有测试用例（用于回归测试）
            
        Returns:
            优化结果
        """
        prompt_file = self.project_dir / self.config.agent.prompt_file
        
        if not prompt_file.exists():
            return OptimizationResult(
                success=False,
                error_message=f"提示词文件不存在: {prompt_file}"
            )
        
        original_prompt = prompt_file.read_text(encoding="utf-8")
        current_prompt = original_prompt
        
        for iteration in range(self.config.optimization.max_iterations):
            # 构建诊断信息
            diagnoses_str = "\n".join([
                f"- 用例 {d.case_id}:\n"
                f"  类别: {d.category.value}\n"
                f"  原因: {d.root_cause}\n"
                f"  建议: {d.suggestion}"
                for d in diagnoses
            ])
            
            prompt = self.optimize_prompt.format(
                current_prompt=current_prompt,
                diagnoses=diagnoses_str
            )
            
            try:
                response = await self.llm.chat(
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # 提取优化后的提示词
                new_prompt = self._extract_optimized_prompt(response)
                
                if not new_prompt:
                    return OptimizationResult(
                        success=False,
                        iterations=iteration + 1,
                        error_message="无法从 LLM 响应中提取优化后的提示词"
                    )
                
                # 写入文件
                prompt_file.write_text(new_prompt, encoding="utf-8")
                
                # 回归测试（如果启用）
                if self.config.optimization.run_regression:
                    from agent_evo.core.generator import Generator
                    from agent_evo.core.evaluator import Evaluator
                    
                    generator = Generator(self.config, self.project_dir)
                    evaluator = Evaluator(self.config)
                    
                    # 重新加载 adapter 以使用新提示词
                    generator.adapter = generator._create_adapter()
                    
                    results = await generator.run_all(test_cases)
                    report = await evaluator.evaluate_all(results)
                    
                    if report.pass_rate >= self.config.optimization.regression_threshold:
                        return OptimizationResult(
                            success=True,
                            iterations=iteration + 1,
                            original_prompt=original_prompt,
                            optimized_prompt=new_prompt,
                            fixed_cases=[d.case_id for d in diagnoses],
                            regression_pass_rate=report.pass_rate
                        )
                    
                    # 未达标，继续迭代
                    current_prompt = new_prompt
                else:
                    # 不做回归测试，直接返回成功
                    return OptimizationResult(
                        success=True,
                        iterations=iteration + 1,
                        original_prompt=original_prompt,
                        optimized_prompt=new_prompt,
                        fixed_cases=[d.case_id for d in diagnoses]
                    )
                    
            except Exception as e:
                # 恢复原始提示词
                prompt_file.write_text(original_prompt, encoding="utf-8")
                
                return OptimizationResult(
                    success=False,
                    iterations=iteration + 1,
                    error_message=str(e)
                )
        
        # 达到最大迭代次数
        return OptimizationResult(
            success=False,
            iterations=self.config.optimization.max_iterations,
            original_prompt=original_prompt,
            optimized_prompt=current_prompt,
            error_message="达到最大迭代次数，未能完全修复"
        )
    
    def _extract_optimized_prompt(self, response: str) -> Optional[str]:
        """从 LLM 响应中提取优化后的提示词"""
        # 尝试匹配 <optimized_prompt> 标签
        match = re.search(
            r'<optimized_prompt>(.*?)</optimized_prompt>',
            response,
            re.DOTALL
        )
        
        if match:
            return match.group(1).strip()
        
        # 如果没有标签，返回整个响应（去除可能的解释文本）
        # 这是一个降级策略
        lines = response.strip().split('\n')
        
        # 查找可能的提示词开始位置
        start_markers = ['#', '你是', '你好', 'You are', 'As a']
        for i, line in enumerate(lines):
            if any(line.strip().startswith(m) for m in start_markers):
                return '\n'.join(lines[i:]).strip()
        
        return None
