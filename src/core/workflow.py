# src/core/workflow.py
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from typing import List, Dict
import traceback

from src.data.loader import read_and_validate_excel, get_source_name
from src.analysis.comparison import analyze_two_versions
from src.analysis import historical, comparison
from src.llm.client import get_llm_client, request_llm_analysis
from src.llm.prompts import create_comparison_prompt, create_historical_prompt
from src.utils.file_handler import save_text_file, save_markdown_report

def format_comparison_results_for_llm(
    results: Dict[str, pd.DataFrame],
    value_column: str,
    examples_count: int = 5
) -> str:
    """将结构化的比对分析结果格式化为一份人类可读的、给LLM的Markdown报告。"""
    added_df = results['added']
    deleted_df = results['deleted']
    modified_df = results['modified']

    num_added = len(added_df)
    num_deleted = len(deleted_df)
    num_modified = len(modified_df)

    if num_added == 0 and num_deleted == 0 and num_modified == 0:
        return "" # 返回空字符串，表示没有差异

    report_parts = [
        f"对比摘要：【新增】{num_added}条，【删除】{num_deleted}条，【修改】{num_modified}条。"
    ]

    if not modified_df.empty:
        report_parts.append("\n---")
        report_parts.append(f"### **核心变更分析 (Top {examples_count} 异常得分榜)**")
        report_parts.append(f"本榜单追踪核心数值列`{value_column}`的变化，按异常得分（变化率）降序排列。")
        modified_df_display = modified_df.head(examples_count).copy()
        modified_df_display['异常得分'] = modified_df_display['异常得分'].apply(
            lambda x: f"∞" if np.isinf(x) else f"{x:.2f}"
        )
        report_parts.append(modified_df_display.to_markdown(index=False))

    if not added_df.empty:
        report_parts.append("\n---")
        report_parts.append(f"### **新增记录示例 (前 {examples_count} 条)**")
        report_parts.append(added_df.head(examples_count).to_markdown(index=False))

    if not deleted_df.empty:
        report_parts.append("\n---")
        report_parts.append(f"### **删除记录示例 (前 {examples_count} 条)**")
        report_parts.append(deleted_df.head(examples_count).to_markdown(index=False))

    return "\n\n".join(report_parts)


def execute_comparison_workflow(
    analysis_tasks: List[Dict],
    analysis_params: Dict,
    llm_config: Dict,
    output_config: Dict
):
    """
    执行双版本对比分析工作流。
    该函数是一个生成器，会流式返回大模型的分析结果，并在结束后保存完整报告。
    """
    try:
        key_columns = analysis_params['keyColumns']
        value_column = analysis_params['valueColumn']
        log_dir = output_config.get('log_directory', './logs')

        hist_task, latest_task = analysis_tasks[0], analysis_tasks[1]
        hist_name, latest_name = get_source_name(hist_task), get_source_name(latest_task)

        print(f"  - 正在读取历史版本: {hist_name}...")
        df_hist = read_and_validate_excel(hist_task['file'], key_columns + [value_column], hist_task.get('sheet'))
        print(f"  - 正在读取最新版本: {latest_name}...")
        df_latest = read_and_validate_excel(latest_task['file'], key_columns + [value_column], latest_task.get('sheet'))

        print("  - 正在进行结构化差异分析...")
        analysis_result = analyze_two_versions(df_hist, df_latest, key_columns, value_column)
        diff_report_for_llm = format_comparison_results_for_llm(analysis_result, value_column)



        if not diff_report_for_llm:
            print("✅ 文件内容在关键指标上完全一致，无需调用大模型。")
            yield f"## ✅ 分析完成：文件内容一致\n\n经过高精度比对，系统确认您上传的两个文件 **{hist_name}** 和 **{latest_name}** 在指定的关键列和数值列上内容完全一致。"
            return

        prompt = create_comparison_prompt(diff_report_for_llm, hist_name, latest_name)
        print("\n📝 正在生成对比分析Prompt...")
        save_text_file(f'{log_dir}/prompts', 'precise_comparison_prompt', prompt)

        print("🤖 正在请求大模型进行流式分析...")
        llm_client = get_llm_client()

        full_response_parts = []
        response_generator = request_llm_analysis(
            client=llm_client,
            model=llm_config.get('model_name', 'qwen-long'),
            system_prompt=llm_config.get('system_prompts', {}).get('comparison', 'You are a helpful data analyst.'),
            user_prompt=prompt
        )

        for chunk in response_generator:
            full_response_parts.append(chunk)
            yield chunk

        assistant_response = "".join(full_response_parts)
        save_text_file(f'{log_dir}/results', 'precise_comparison_result', assistant_response)

        report_dir = output_config.get('report_directory', '.')
        print(f"\n✅ **最终综合分析报告** 已保存到指定目录：{report_dir}")
        save_markdown_report(report_dir, 'Precise_Comparison_Report', assistant_response)

    except Exception as e:
        print(f"❌ 在执行对比分析工作流时发生严重错误: {e}")
        traceback.print_exc()
        yield f"\n\n后台错误：{str(e)}"
        raise e

def execute_historical_workflow(
    analysis_tasks: List[Dict],
    analysis_params: Dict,
    llm_config: Dict,
    output_config: Dict
):
    """
    执行多版本历史追溯分析工作流。
    该函数是一个生成器，会流式返回大模型的分析结果，并在结束后保存完整报告。
    """
    try:
        key_columns = analysis_params['keyColumns']
        value_column = analysis_params['valueColumn']
        top_n = analysis_params.get('topN', 15)
        log_dir = output_config.get('log_directory', './logs')

        all_dfs = []
        for i, task in enumerate(analysis_tasks):
            source_name = get_source_name(task)
            print(f"  - 正在读取版本 {i + 1}: {source_name}")
            df_formatted = read_and_validate_excel(task['file'], key_columns + [value_column], task.get('sheet'))
            all_dfs.append(df_formatted)

        trace_df = historical.generate_historical_trace_table(all_dfs, key_columns, value_column, top_n)

        print(trace_df)

        md_trace_table = historical.create_historical_trace_markdown(trace_df, key_columns)


        if "未发现任何记录的核心数值发生过变化" in md_trace_table:
             print("✅ 多版本文件核心数值一致，未发现差异，无需调用大模型。")
             yield f"## ✅ 分析完成：核心数值无变化\n\n经过多版本历史追溯，系统确认在所有文件中，您指定的数值列 **{value_column}** 未发生任何变化。"
             return

        df_first = all_dfs[0]
        df_last = all_dfs[-1]
        summary_diff_report = comparison.generate_precise_diff_report(df_first, df_last, key_columns, columns_to_check=[value_column])
        summary_line = summary_diff_report.split('\n')[0]
        source_names = " -> ".join([get_source_name(task) for task in analysis_tasks])

        prompt = create_historical_prompt(
            md_trace_table, summary_line, source_names, value_column, len(trace_df)
        )
        print("\n📝 正在生成历史追溯Prompt...")
        save_text_file(f'{log_dir}/prompts', 'historical_trace_prompt', prompt)

        print("🤖 正在请求大模型进行流式分析...")
        llm_client = get_llm_client()

        full_response_parts = []
        response_generator = request_llm_analysis(
            client=llm_client,
            model=llm_config.get('model_name', 'qwen-long'),
            system_prompt=llm_config.get('system_prompts', {}).get('historical', 'You are a helpful data analyst.'),
            user_prompt=prompt
        )

        for chunk in response_generator:
            full_response_parts.append(chunk)
            yield chunk

        assistant_response = "".join(full_response_parts)
        save_text_file(f'{log_dir}/results', 'historical_trace_result', assistant_response)

        report_dir = output_config.get('report_directory', '.')
        print(f"\n✅ **最终综合分析报告**: 已保存到指定目录：{report_dir}")
        save_markdown_report(report_dir, 'Historical_Trace_Report', assistant_response)

    except Exception as e:
        print(f"❌ 在执行历史追溯工作流时发生严重错误: {e}")
        traceback.print_exc()
        yield f"\n\n后台错误：{str(e)}"
        raise e