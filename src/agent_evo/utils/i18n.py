"""国际化支持 / Internationalization support

提供中英文报告文案切换能力。
Provides Chinese/English report text switching.
"""

from typing import Literal

# 当前语言（默认中文）/ Current language (default Chinese)
_current_lang: Literal["zh", "en"] = "zh"


def set_language(lang: Literal["zh", "en"]) -> None:
    """设置当前语言 / Set current language"""
    global _current_lang
    _current_lang = lang


def get_language() -> Literal["zh", "en"]:
    """获取当前语言 / Get current language"""
    return _current_lang


def t(key: str) -> str:
    """根据 key 返回当前语言的文案 / Return text for current language by key"""
    entry = _TEXTS.get(key)
    if entry is None:
        return key
    return entry.get(_current_lang, entry.get("zh", key))


# ── 文案映射表 / Text mapping table ──────────────────────────

_TEXTS: dict[str, dict[str, str]] = {
    # ── 通用 / General ──
    "pass": {"zh": "通过", "en": "PASS"},
    "fail": {"zh": "失败", "en": "FAIL"},
    "warn": {"zh": "警告", "en": "WARN"},
    "error": {"zh": "错误", "en": "ERROR"},
    "skipped": {"zh": "跳过", "en": "SKIPPED"},
    "total": {"zh": "总计", "en": "Total"},
    "passed": {"zh": "通过", "en": "Passed"},
    "failed": {"zh": "失败", "en": "Failed"},
    "score": {"zh": "评分", "en": "Score"},
    "summary": {"zh": "摘要", "en": "Summary"},
    "duration": {"zh": "耗时", "en": "Duration"},
    "pass_rate": {"zh": "通过率", "en": "Pass Rate"},

    # ── Pipeline ──
    "pipeline_start": {"zh": "AgentEvo Pipeline 启动", "en": "AgentEvo Pipeline Started"},
    "loaded_cases": {"zh": "加载了 {n} 个测试用例", "en": "Loaded {n} test cases"},
    "phase_a": {"zh": "Phase A: 批量执行 + 因子化评测", "en": "Phase A: Batch Execution + Factor-based Evaluation"},
    "phase_b": {"zh": "Phase B: 聚合归因分析", "en": "Phase B: Aggregated Root Cause Analysis"},
    "phase_c": {"zh": "Phase C: 统一优化 + 回归验证", "en": "Phase C: Unified Optimization + Regression"},
    "phase_d": {"zh": "Phase D: 创建 PR", "en": "Phase D: Create PR"},
    "found_patterns": {"zh": "发现 {n} 个共性模式", "en": "Found {n} common patterns"},
    "dry_run_mode": {"zh": "Dry-run 模式，不实际修改文件", "en": "Dry-run mode, no actual file modifications"},
    "optimize_success": {"zh": "优化成功！迭代 {n} 次", "en": "Optimization succeeded! {n} iterations"},
    "optimize_fail": {"zh": "优化未能完全解决问题: {msg}", "en": "Optimization could not fully resolve issues: {msg}"},
    "no_auto_fix_patterns": {"zh": "未找到可自动修复的共性模式", "en": "No auto-fixable common patterns found"},
    "pr_created": {"zh": "PR 已创建: {url}", "en": "PR created: {url}"},
    "pipeline_success": {"zh": "Pipeline 执行成功", "en": "Pipeline execution succeeded"},
    "pipeline_done_with_failures": {"zh": "Pipeline 执行完成，存在失败用例", "en": "Pipeline completed with failures"},

    # ── eval 报告 / Eval report ──
    "eval_report_title": {"zh": "📊 评测报告", "en": "📊 Evaluation Report"},
    "eval_result": {"zh": "评测结果", "en": "Evaluation Result"},
    "detailed_results": {"zh": "详细结果:", "en": "Detailed Results:"},
    "report_saved": {"zh": "📄 报告已保存: {path}", "en": "📄 Report saved: {path}"},
    "eval_failed": {"zh": "❌ 评测失败: {msg}", "en": "❌ Evaluation failed: {msg}"},

    # ── 因子 / Factors ──
    "factor_summary_title": {"zh": "因子汇总:", "en": "Factor Summary:"},
    "factor_line": {
        "zh": "{fid}: 激活 {activated} 次, 平均分 {avg:.2f}, 失败 {fail} 次",
        "en": "{fid}: activated {activated} times, avg score {avg:.2f}, failed {fail} times",
    },
    "fatal_factor_fail": {
        "zh": "致命因子 {fid} 未通过: {reason}",
        "en": "Fatal factor {fid} failed: {reason}",
    },
    "fatal_factor_summary": {
        "zh": "致命因子 {fid} 失败",
        "en": "Fatal factor {fid} failed",
    },
    "weighted_score_summary": {
        "zh": "加权总分: {score:.2f}",
        "en": "Weighted score: {score:.2f}",
    },
    "weighted_below_threshold": {
        "zh": "加权总分 {score:.2f} < 阈值 {threshold}",
        "en": "Weighted score {score:.2f} < threshold {threshold}",
    },
    "no_factor_activated": {
        "zh": "无评测因子被激活，默认通过",
        "en": "No evaluation factor activated, passed by default",
    },
    "exec_error": {"zh": "执行错误: {err}", "en": "Execution error: {err}"},
    "dim_pass": {"zh": "{dim} 达标", "en": "{dim} passed"},

    # ── gate-check / 门禁检查 ──
    "gate_check_title": {"zh": "门禁检查: 检查 {tags} 标签", "en": "Gate Check: checking tags {tags}"},
    "gate_check_skip": {
        "zh": "未配置任何 required_for_release 的 tag_policies，门禁检查跳过",
        "en": "No required_for_release tag_policies configured, gate check skipped",
    },
    "gate_check_pass": {"zh": "门禁检查通过", "en": "Gate check passed"},
    "gate_check_fail": {"zh": "门禁检查失败，阻断发布", "en": "Gate check failed, release blocked"},
    "gate_no_cases": {"zh": "无用例", "en": "No cases"},
    "release_blocked": {
        "zh": "门禁阻断: {tags} 未达标",
        "en": "Release blocked: {tags} did not meet threshold",
    },

    # ── 失败用例 / Failed cases ──
    "failed_cases_title": {"zh": "失败用例:", "en": "Failed Cases:"},

    # ── stats 命令 / stats command ──
    "stats_title": {"zh": "测评集统计", "en": "Test Suite Statistics"},
    "stats_total": {"zh": "共 {n} 条用例", "en": "{n} test cases in total"},
    "by_tier": {"zh": "按层级", "en": "By Tier"},
    "by_tag": {"zh": "按标签", "en": "By Tag"},
    "by_source": {"zh": "按来源", "en": "By Source"},
    "tier": {"zh": "层级", "en": "Tier"},
    "tag": {"zh": "标签", "en": "Tag"},
    "source": {"zh": "来源", "en": "Source"},
    "count": {"zh": "数量", "en": "Count"},
    "pending_review": {
        "zh": "有 {n} 条用例待审核",
        "en": "{n} cases pending review",
    },

    # ── import 命令 / import command ──
    "importing": {"zh": "正在导入 {path} (格式: {fmt})", "en": "Importing {path} (format: {fmt})"},
    "import_done": {"zh": "导入完成", "en": "Import completed"},
    "total_records": {"zh": "总记录数", "en": "Total records"},
    "imported_count": {"zh": "成功导入", "en": "Successfully imported"},
    "dedup_removed": {"zh": "去重移除", "en": "Duplicates removed"},
    "pending_count": {"zh": "待审核", "en": "Pending review"},
    "output_file": {"zh": "输出文件", "en": "Output file"},
    "no_cases_imported": {"zh": "未导入任何用例", "en": "No cases imported"},
    "import_review_hint": {
        "zh": "所有用例状态为 pending，请通过 agent-evo review 审核",
        "en": "All cases are pending, please review via agent-evo review",
    },
    "source_not_found": {
        "zh": "未找到数据源: {name}",
        "en": "Data source not found: {name}",
    },
    "available_sources": {"zh": "可用数据源", "en": "Available sources"},
    "fetching_source": {
        "zh": "正在从数据源 [{name}] 拉取数据: {url}",
        "en": "Fetching from source [{name}]: {url}",
    },
    "fetch_source_error": {
        "zh": "数据源拉取失败: {err}",
        "en": "Failed to fetch from source: {err}",
    },

    # ── mutate 命令 / mutate command ──
    "loaded_seeds": {"zh": "加载了 {n} 条种子用例", "en": "Loaded {n} seed cases"},
    "mutate_per_seed": {"zh": "每条种子生成 {n} 个变异...", "en": "Generating {n} mutations per seed..."},
    "generated_mutations": {"zh": "生成了 {n} 条变异用例", "en": "Generated {n} mutation cases"},
    "llm_reviewing": {"zh": "LLM 预审中...", "en": "LLM pre-reviewing..."},
    "review_rejected": {"zh": "预审拒绝 {n} 条", "en": "{n} cases rejected by pre-review"},
    "written_cases": {"zh": "已写入 {n} 条用例到 {path}", "en": "Written {n} cases to {path}"},
    "mutate_review_hint": {
        "zh": "所有用例状态为 pending，请通过 agent-evo review 审核",
        "en": "All cases are pending, please review via agent-evo review",
    },

    # ── review 命令 / review command ──
    "no_test_files": {"zh": "未找到测试文件", "en": "No test files found"},
    "no_status_cases": {"zh": "没有 {status} 状态的用例", "en": "No cases with status {status}"},
    "found_pending": {"zh": "找到 {n} 条 {status} 状态的用例", "en": "Found {n} cases with status {status}"},
    "batch_approved": {"zh": "已将 {n} 条用例全部标记为 approved", "en": "Marked all {n} cases as approved"},
    "interactive_hint": {"zh": "交互式审核（a=通过, r=拒绝, s=跳过）", "en": "Interactive review (a=approve, r=reject, s=skip)"},
    "review_result": {"zh": "通过 {a} 条, 拒绝 {r} 条", "en": "Approved {a}, rejected {r}"},

    # ── report 表头 / report table headers ──
    "col_id": {"zh": "ID", "en": "ID"},
    "col_name": {"zh": "名称", "en": "Name"},
    "col_status": {"zh": "状态", "en": "Status"},
    "col_score": {"zh": "评分", "en": "Score"},
    "col_summary": {"zh": "摘要", "en": "Summary"},
    "col_mutation_strategy": {"zh": "变异方式", "en": "Mutation Strategy"},
    "col_input": {"zh": "输入", "en": "Input"},

    # ── HTML 报告 / HTML report ──
    "html_title": {"zh": "AgentEvo 评测报告", "en": "AgentEvo Evaluation Report"},
    "html_overview": {"zh": "概览", "en": "Overview"},
    "html_detailed": {"zh": "详细结果", "en": "Detailed Results"},

    # ── init 命令 / init command ──
    "init_project": {"zh": "初始化 AgentEvo 项目", "en": "Initializing AgentEvo project"},
    "init_created": {"zh": "创建文件", "en": "Created file"},
    "init_exists": {"zh": "文件已存在", "en": "File already exists"},
    "init_done": {"zh": "初始化完成！", "en": "Initialization complete!"},
    "init_next_steps": {"zh": "下一步:", "en": "Next steps:"},
    "init_step_agent": {
        "zh": "编辑 [cyan]agent.py[/cyan] 实现你的 Agent 逻辑",
        "en": "Edit [cyan]agent.py[/cyan] to implement your Agent logic",
    },
    "init_step_prompt": {
        "zh": "编辑 [cyan]system_prompt.md[/cyan] 定义系统提示词",
        "en": "Edit [cyan]system_prompt.md[/cyan] to define system prompt",
    },
    "init_step_tests": {
        "zh": "编辑 [cyan]tests/basic.yaml[/cyan] 添加测试用例",
        "en": "Edit [cyan]tests/basic.yaml[/cyan] to add test cases",
    },
    "init_step_eval": {
        "zh": "运行 [cyan]agent-evo eval[/cyan] 开始评测",
        "en": "Run [cyan]agent-evo eval[/cyan] to start evaluation",
    },
    "init_step_run": {
        "zh": "运行 [cyan]agent-evo auto[/cyan] 一站式评测 + 自动优化",
        "en": "Run [cyan]agent-evo auto[/cyan] for one-stop evaluation + auto-optimization",
    },

    # ── auto 命令 / auto command ──
    "auto_start": {
        "zh": "🚀 一站式自动评测 + 优化启动",
        "en": "🚀 One-stop auto evaluation + optimization started",
    },
    "auto_success": {
        "zh": "✅ 评测全部通过，无需优化",
        "en": "✅ All tests passed, no optimization needed",
    },
    "auto_optimized": {
        "zh": "✅ 自动优化完成，提示词已更新",
        "en": "✅ Auto-optimization completed, prompt updated",
    },
    "auto_partial": {
        "zh": "⚠️ 优化已尝试，仍有失败用例需人工排查",
        "en": "⚠️ Optimization attempted, some cases still need manual review",
    },

    # ── run 命令 / run command ──
    "exec_failed": {"zh": "执行失败: {msg}", "en": "Execution failed: {msg}"},

    # ── 状态显示 / Status display ──
    "status_passed": {"zh": "✅ 通过", "en": "✅ Passed"},
    "status_failed": {"zh": "❌ 失败", "en": "❌ Failed"},
    "status_error": {"zh": "⚠ 错误", "en": "⚠ Error"},
    "status_skipped": {"zh": "⏭ 跳过", "en": "⏭ Skipped"},

    # ── 错误信息 / Error messages ──
    "config_not_found": {
        "zh": "未找到配置文件。请运行 `agent-evo init` 初始化项目，或指定配置文件路径。",
        "en": "Config file not found. Run `agent-evo init` to initialize, or specify config path.",
    },
    "config_file_missing": {"zh": "配置文件不存在: {path}", "en": "Config file not found: {path}"},
    "unsupported_provider": {"zh": "不支持的 LLM 提供商: {provider}", "en": "Unsupported LLM provider: {provider}"},
    "agent_load_fail": {
        "zh": "无法加载 Agent: {path}\n请确保模块存在且函数已导出。\n错误: {err}",
        "en": "Cannot load Agent: {path}\nEnsure the module exists and the function is exported.\nError: {err}",
    },
    "http_adapter_request_fail": {
        "zh": "HTTP 请求失败: {url}\n状态码: {status}\n错误: {err}",
        "en": "HTTP request failed: {url}\nStatus: {status}\nError: {err}",
    },
    "http_adapter_stream_error": {
        "zh": "Agent 返回流式错误 (code={code}): {msg}",
        "en": "Agent returned streaming error (code={code}): {msg}",
    },

    # ── 其他 / Others ──
    "unsupported_format": {"zh": "不支持的格式: {fmt}", "en": "Unsupported format: {fmt}"},
    "no_valid_records": {"zh": "未解析到有效记录", "en": "No valid records parsed"},
    "missing_keywords": {"zh": "缺少关键词: {kw}", "en": "Missing keywords: {kw}"},
    "forbidden_keywords": {"zh": "包含禁止词: {kw}", "en": "Contains forbidden words: {kw}"},
    "output_not_json": {"zh": "输出不是有效的 JSON", "en": "Output is not valid JSON"},
    "json_mismatch": {"zh": "JSON 不完全匹配", "en": "JSON does not match exactly"},
    "jsonschema_skip": {"zh": "jsonschema 库未安装，跳过校验", "en": "jsonschema not installed, skipping"},
    "jsonpath_skip": {"zh": "jsonpath-ng 库未安装，跳过校验", "en": "jsonpath-ng not installed, skipping"},
    "path_not_exist": {"zh": "路径 {path} 不存在", "en": "Path {path} does not exist"},
    "path_no_value": {"zh": "路径 {path} 未找到值", "en": "No value found at path {path}"},
    "unsupported_operator": {"zh": "不支持的算子: {op}", "en": "Unsupported operator: {op}"},
    "expect_actual": {
        "zh": "期望 {op} {expected}，实际为 {actual}",
        "en": "Expected {op} {expected}, got {actual}",
    },
    "custom_check_fail": {"zh": "自定义校验未通过", "en": "Custom validation failed"},
    "custom_check_error": {"zh": "自定义校验出错: {err}", "en": "Custom validation error: {err}"},
    "no_custom_check": {"zh": "无自定义校验", "en": "No custom validation"},
    "llm_judge_error": {"zh": "LLM 评判出错: {err}", "en": "LLM judge error: {err}"},
    "process_record_fail": {"zh": "处理记录失败: {err}", "en": "Failed to process record: {err}"},
    "common_fail_count": {"zh": "共 {n} 条用例失败", "en": "{n} cases failed in total"},
    "suggest_manual_check": {"zh": "建议人工检查失败用例的因子归因", "en": "Suggest manual inspection of factor attributions for failed cases"},

    # ── behavior 维度校验 / behavior dimension checks ──
    "tool_not_called": {"zh": "必需工具 {tool} 未被调用", "en": "Required tool {tool} was not called"},
    "tool_missing_params": {"zh": "工具 {tool} 缺少必需参数: {params}", "en": "Tool {tool} missing required params: {params}"},
    "tool_wrong_params": {"zh": "工具 {tool} 参数值不匹配: {details}", "en": "Tool {tool} param values mismatch: {details}"},
    "tool_forbidden_called": {"zh": "调用了禁止的工具: {tools}", "en": "Forbidden tools were called: {tools}"},
    "tool_max_calls_exceeded": {"zh": "工具调用次数 {actual} 超过最大限制 {max}", "en": "Tool call count {actual} exceeded max limit {max}"},
    "tool_sequence_mismatch": {"zh": "工具调用序列不匹配: 期望 {expected}, 实际 {actual}", "en": "Tool call sequence mismatch: expected {expected}, got {actual}"},
    "tool_sequence_missing": {"zh": "缺少必需的工具调用: {tools}", "en": "Missing required tool calls: {tools}"},
}
