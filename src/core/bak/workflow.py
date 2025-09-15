# -*- coding: utf-8 -*-

import pandas as pd
from typing import List, Dict

# 从项目模块中导入
from src.data.loader import read_and_validate_excel, apply_formatting_rules, get_source_name
from src.analysis import comparison, historical
from src.llm.client import get_llm_client, request_llm_analysis
from src.llm.prompts import create_comparison_prompt, create_historical_prompt
from src.utils.file_handler import save_text_file, save_markdown_report

def execute_comparison_workflow(analysis_tasks: List[Dict], config: Dict):
    """执行双版本高精度比对分析工作流。"""
    try:
        # --- 配置提取 ---
        key_columns = config['analysis_params']['key_columns']
        formatting_rules = config['analysis_params']['formatting_rules']
        llm_config = config['llm']
        output_config = config['output']
        log_dir = output_config['log_directory']

        # --- 数据加载 ---
        hist_task, latest_task = analysis_tasks[0], analysis_tasks[1]
        hist_name, latest_name = get_source_name(hist_task), get_source_name(latest_task)

        print(f"  - 正在读取历史版本: {hist_name}...")
        df_hist_raw = read_and_validate_excel(hist_task['file'], key_columns, hist_task.get('sheet'))
        print(f"  - 正在读取最新版本: {latest_name}...")
        df_latest_raw = read_and_validate_excel(latest_task['file'], key_columns, latest_task.get('sheet'))

        # --- 数据预处理 ---
        print("  - 正在应用自定义格式化规则...")
        df_hist = apply_formatting_rules(df_hist_raw, formatting_rules)
        df_latest = apply_formatting_rules(df_latest_raw, formatting_rules)

        # --- 核心分析 ---
        print("  - 正在生成差异报告...")
        diff_report = comparison.generate_precise_diff_report(df_hist, df_latest, key_columns, hist_name, latest_name)

        # --- LLM 交互 ---
        prompt = create_comparison_prompt(diff_report, hist_name, latest_name)
        print("\n📝 正在生成对比分析Prompt...")
        save_text_file(f'{log_dir}/prompts', 'precise_comparison_prompt', prompt)

        print("🤖 正在请求大模型进行分析...")
        llm_client = get_llm_client()
        assistant_response = request_llm_analysis(
            client=llm_client,
            model=llm_config['model_name'],
            system_prompt=llm_config['system_prompts']['comparison'],
            user_prompt=prompt
        )
        save_text_file(f'{log_dir}/results', 'precise_comparison_result', assistant_response)

        # --- 结果保存 ---
        print(f"\n✅ **最终综合分析报告** 已保存到指定目录：{output_config['report_directory']}")
        save_markdown_report(output_config['report_directory'], 'Precise_Comparison_Report', assistant_response)
        return assistant_response

    except Exception as e:
        print(f"❌ 在执行对比分析工作流时发生严重错误: {e}")
        import traceback
        traceback.print_exc()

def execute_historical_workflow(analysis_tasks: List[Dict], config: Dict):
    """执行多版本历史追溯分析工作流。"""
    try:
        # --- 配置提取 ---
        params = config['analysis_params']
        key_columns, value_column = params['key_columns'], params['value_column']
        formatting_rules, top_n = params['formatting_rules'], params['top_n_for_analysis']
        llm_config = config['llm']
        output_config = config['output']
        log_dir = output_config['log_directory']

        # --- 数据加载与预处理 ---
        all_dfs = []
        for i, task in enumerate(analysis_tasks):
            source_name = get_source_name(task)
            print(f"  - 正在读取版本 {i + 1}: {source_name}")
            df_raw = read_and_validate_excel(task['file'], key_columns, task.get('sheet'))
            df_formatted = apply_formatting_rules(df_raw, formatting_rules)
            all_dfs.append(df_formatted)

        # --- 核心分析 ---
        trace_df = historical.generate_historical_trace_table(all_dfs, key_columns, value_column, top_n)
        md_trace_table = historical.create_historical_trace_markdown(trace_df, key_columns)

        # 为摘要准备首尾版本对比
        df_first = all_dfs[0]
        df_last = all_dfs[-1]
        summary_diff_report = comparison.generate_precise_diff_report(df_first, df_last, key_columns, columns_to_check=[value_column])
        summary_line = summary_diff_report.split('\n')[0]
        source_names = " -> ".join([get_source_name(task) for task in analysis_tasks])

        # --- LLM 交互 ---
        prompt = create_historical_prompt(
            md_trace_table, summary_line, source_names, value_column, len(trace_df)
        )
        print("\n📝 正在生成历史追溯Prompt...")
        save_text_file(f'{log_dir}/prompts', 'historical_trace_prompt', prompt)

        print("🤖 正在请求大模型进行分析...")
        llm_client = get_llm_client()
        assistant_response = request_llm_analysis(
            client=llm_client,
            model=llm_config['model_name'],
            system_prompt=llm_config['system_prompts']['historical'],
            user_prompt=prompt
        )
        save_text_file(f'{log_dir}/results', 'historical_trace_result', assistant_response)

        # --- 结果保存 ---
        print(f"\n✅ **最终综合分析报告**: 已保存到指定目录：{output_config['report_directory']}")
        save_markdown_report(output_config['report_directory'], 'Historical_Trace_Report', assistant_response)
        return assistant_response

    except Exception as e:
        print(f"❌ 在执行历史追溯工作流时发生严重错误: {e}")
        import traceback
        traceback.print_exc()