# -*- coding: utf-8 -*-

import pandas as pd
from typing import List, Optional, Dict
import numpy as np

def _are_series_equal(s1: pd.Series, s2: pd.Series) -> pd.Series:
    s1_numeric = pd.to_numeric(s1, errors='coerce')
    s2_numeric = pd.to_numeric(s2, errors='coerce')

    if s1_numeric.isnull().all() or s2_numeric.isnull().all():
        return s1.astype(str) == s2.astype(str)
    else:
        return s1_numeric == s2_numeric


def generate_precise_diff_report(
    df_hist: pd.DataFrame,
    df_latest: pd.DataFrame,
    key_columns: List[str],
    hist_name: str = '历史版本',
    latest_name: str = '最新版本',
    # --- 新增参数 ---
    # 允许调用者指定只检查哪些列。如果为None，则检查所有非关键列。
    columns_to_check: Optional[List[str]] = None
) -> str:
    """
    生成高精度的人类可读的数据差异项，对比两个DataFrame。
    """
    hist = df_hist.copy()
    latest = df_latest.copy()

    # 如果未指定检查列，则默认检查所有非关键列
    if columns_to_check is None:
        value_cols = sorted([col for col in df_hist.columns if col not in key_columns])
    else:
        value_cols = columns_to_check

    merged_df = pd.merge(
        hist, latest, on=key_columns, how='outer', suffixes=('_hist', '_latest'), indicator=True
    )

    log_entries = []

    deleted_rows = merged_df[merged_df['_merge'] == 'left_only']
    for _, row in deleted_rows.iterrows():
        key_str = ", ".join([f"{col}: '{row[col]}'" for col in key_columns])
        log_entries.append(f"【删除】源于 {hist_name} 的记录被删除。唯一键: [{key_str}]")

    added_rows = merged_df[merged_df['_merge'] == 'right_only']
    for _, row in added_rows.iterrows():
        key_str = ", ".join([f"{col}: '{row[col]}'" for col in key_columns])
        log_entries.append(f"【新增】在 {latest_name} 发现新记录。唯一键: [{key_str}]")

    both_df = merged_df[merged_df['_merge'] == 'both'].copy()
    modified_keys = set()

    # 现在的 value_cols 可能是所有非关键列，也可能是指定的列
    for col in value_cols:
        col_hist, col_latest = f'{col}_hist', f'{col}_latest'

        are_equal = _are_series_equal(both_df[col_hist], both_df[col_latest])
        diff_mask = ~are_equal

        changed_df = both_df[diff_mask]

        for _, row in changed_df.iterrows():
            key_tuple = tuple(row[k] for k in key_columns)
            modified_keys.add(key_tuple)

            key_str = ", ".join([f"{k}: '{v}'" for k, v in zip(key_columns, key_tuple)])
            log_entries.append(
                f"【修改】唯一键: [{key_str}] | 列 '{col}': 值从 '{row[col_hist]}' 变为 '{row[col_latest]}'"
            )

    summary = f"对比摘要：【新增】{len(added_rows)}条，【删除】{len(deleted_rows)}条，【修改】{len(modified_keys)}条。"
    details = "\n".join(sorted(log_entries))

    return f"  {summary}\n\n--- 详细变更记录 ---\n{details}" if details else summary


def analyze_two_versions(
    df_hist: pd.DataFrame,
    df_latest: pd.DataFrame,
    key_columns: List[str],
    value_column: str
) -> Dict[str, pd.DataFrame]:
    # --- 1. 数据准备和合并 ---
    hist = df_hist.copy()
    latest = df_latest.copy()

    # 将用于分析的数值列转换为数字，无效值设为NaN
    hist[value_column] = pd.to_numeric(hist[value_column], errors='coerce')
    latest[value_column] = pd.to_numeric(latest[value_column], errors='coerce')

    merged_df = pd.merge(
        hist, latest, on=key_columns, how='outer', suffixes=('_hist', '_latest'), indicator=True
    )

    # --- 2. 识别新增和删除的记录 ---
    deleted_rows = merged_df[merged_df['_merge'] == 'left_only'][key_columns + [f'{value_column}_hist']]
    added_rows = merged_df[merged_df['_merge'] == 'right_only'][key_columns + [f'{value_column}_latest']]

    deleted_rows.rename(columns={f'{value_column}_hist': value_column}, inplace=True)
    added_rows.rename(columns={f'{value_column}_latest': value_column}, inplace=True)

    # --- 3. 识别修改的记录并计算异常分数 ---
    both_df = merged_df[merged_df['_merge'] == 'both'].copy()

    val_hist = both_df[f'{value_column}_hist']
    val_latest = both_df[f'{value_column}_latest']

    # 仅保留数值实际发生变化的行
    modified_rows = both_df[val_hist.ne(val_latest) & val_hist.notna() & val_latest.notna()].copy()

    if not modified_rows.empty:
        old_val = modified_rows[f'{value_column}_hist']
        new_val = modified_rows[f'{value_column}_latest']

        # 计算差异和变化率（异常得分）
        diff = new_val - old_val

        # diff取绝对值，避免负数影响排序
        diff = diff.abs()

        # 使用 np.divide 来处理除以0的情况，结果为无穷大
        anomaly_score = np.divide(diff, old_val, where=old_val!=0, out=np.full_like(diff, np.inf)) * 100

        modified_rows['变更前的值'] = old_val
        modified_rows['变更后的值'] = new_val
        modified_rows['差值'] = diff
        modified_rows['异常得分'] = anomaly_score

        # 按异常得分的绝对值降序排序
        modified_rows = modified_rows.sort_values(by='异常得分', ascending=False, key=abs).reset_index(drop=True)

        # 只保留有用的列
        final_cols = key_columns + ['变更前的值', '变更后的值', '差值', '异常得分']
        modified_rows = modified_rows[final_cols]
    else:
        # 如果没有修改，创建一个空的DataFrame以保持结构一致
        modified_rows = pd.DataFrame(columns=key_columns + ['变更前的值', '变更后的值', '差值', '异常得分'])

    return {
        'added': added_rows.reset_index(drop=True),
        'deleted': deleted_rows.reset_index(drop=True),
        'modified': modified_rows,
    }