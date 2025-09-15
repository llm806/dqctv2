# -*- coding: utf-8 -*-

import pandas as pd
from typing import List, Dict
import traceback

# 从项目模块中导入 (保持不变)
from src.data.loader import read_and_validate_excel, get_source_name
from src.analysis import comparison, historical
from src.llm.client import get_llm_client, request_llm_analysis
from src.llm.prompts import create_comparison_prompt, create_historical_prompt
from src.utils.file_handler import save_text_file, save_markdown_report

# 优化: 更新函数签名，解耦配置
def execute_comparison_workflow(
    analysis_tasks: List[Dict],
    analysis_params: Dict,
    llm_config: Dict,
    output_config: Dict
):
    """
    执行双版本高精度比对分析工作流。
    现在由来自UI的动态参数驱动。
    """
    try:
        # --- 1. 从传入的参数中提取配置 ---
        # 关键列由前端用户动态指定
        key_columns = analysis_params['keyColumns']
        log_dir = output_config.get('log_directory', './logs')

        # --- 2. 数据加载 ---
        hist_task, latest_task = analysis_tasks[0], analysis_tasks[1]
        hist_name, latest_name = get_source_name(hist_task), get_source_name(latest_task)

        print(f"  - 正在读取历史版本: {hist_name}...")
        # 验证时使用动态传入的 key_columns
        df_hist = read_and_validate_excel(hist_task['file'], key_columns, hist_task.get('sheet'))
        print(f"  - 正在读取最新版本: {latest_name}...")
        df_latest = read_and_validate_excel(latest_task['file'], key_columns, latest_task.get('sheet'))

        # --- 3. 核心分析 ---
        print("  - 正在生成差异报告...")
        diff_report = comparison.generate_precise_diff_report(df_hist, df_latest, key_columns, hist_name, latest_name)

        # --- 4. LLM 交互 ---
        prompt = create_comparison_prompt(diff_report, hist_name, latest_name)
        print("\n📝 正在生成对比分析Prompt...")
        save_text_file(f'{log_dir}/prompts', 'precise_comparison_prompt', prompt)

        print("🤖 正在请求大模型进行分析...")
        llm_client = get_llm_client()
        assistant_response = request_llm_analysis(
            client=llm_client,
            model=llm_config.get('model_name', 'qwen-long'), # 使用 .get() 增加健壮性
            system_prompt=llm_config.get('system_prompts', {}).get('comparison', 'You are a helpful data analyst.'),
            user_prompt=prompt
        )
        save_text_file(f'{log_dir}/results', 'precise_comparison_result', assistant_response)

        # --- 5. 结果保存 ---
        report_dir = output_config.get('report_directory', '.')
        print(f"\n✅ **最终综合分析报告** 已保存到指定目录：{report_dir}")
        save_markdown_report(report_dir, 'Precise_Comparison_Report', assistant_response)
        return assistant_response

    except Exception as e:
        print(f"❌ 在执行对比分析工作流时发生严重错误: {e}")
        traceback.print_exc()
        # 抛出异常，让上层服务捕获并返回给前端
        raise e

# 优化: 更新函数签名，解耦配置
def execute_historical_workflow(
    analysis_tasks: List[Dict],
    analysis_params: Dict,
    llm_config: Dict,
    output_config: Dict
):
    """
    执行多版本历史追溯分析工作流。
    现在由来自UI的动态参数驱动。
    """
    try:
        # --- 1. 从传入的参数中提取配置 ---
        key_columns = analysis_params['keyColumns']
        value_column = analysis_params['valueColumn']
        # top_n 作为一个可选参数，提供默认值
        top_n = analysis_params.get('topN', 15)
        log_dir = output_config.get('log_directory', './logs')

        # --- 2. 数据加载与预处理 ---
        all_dfs = []
        for i, task in enumerate(analysis_tasks):
            source_name = get_source_name(task)
            print(f"  - 正在读取版本 {i + 1}: {source_name}")
            # 不再应用静态的格式化规则，以保持通用性
            df_formatted = read_and_validate_excel(task['file'], key_columns + [value_column], task.get('sheet'))
            all_dfs.append(df_formatted)

        # --- 3. 核心分析 ---
        trace_df = historical.generate_historical_trace_table(all_dfs, key_columns, value_column, top_n)
        md_trace_table = historical.create_historical_trace_markdown(trace_df, key_columns)

        df_first = all_dfs[0]
        df_last = all_dfs[-1]
        summary_diff_report = comparison.generate_precise_diff_report(df_first, df_last, key_columns, columns_to_check=[value_column])
        summary_line = summary_diff_report.split('\n')[0]
        source_names = " -> ".join([get_source_name(task) for task in analysis_tasks])

        # --- 4. LLM 交互 ---
        prompt = create_historical_prompt(
            md_trace_table, summary_line, source_names, value_column, len(trace_df)
        )
        print("\n📝 正在生成历史追溯Prompt...")
        save_text_file(f'{log_dir}/prompts', 'historical_trace_prompt', prompt)

        print("🤖 正在请求大模型进行分析...")
        llm_client = get_llm_client()
        assistant_response = request_llm_analysis(
            client=llm_client,
            model=llm_config.get('model_name', 'qwen-long'),
            system_prompt=llm_config.get('system_prompts', {}).get('historical', 'You are a helpful data analyst.'),
            user_prompt=prompt
        )
        save_text_file(f'{log_dir}/results', 'historical_trace_result', assistant_response)

        # --- 5. 结果保存 ---
        report_dir = output_config.get('report_directory', '.')
        print(f"\n✅ **最终综合分析报告**: 已保存到指定目录：{report_dir}")
        save_markdown_report(report_dir, 'Historical_Trace_Report', assistant_response)
        return assistant_response

    except Exception as e:
        print(f"❌ 在执行历史追溯工作流时发生严重错误: {e}")
        traceback.print_exc()
        # 抛出异常，让上层服务捕获并返回给前端
        raise e