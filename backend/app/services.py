# backend/app/services.py
import os
import shutil
import tempfile
from typing import List, Dict
from fastapi import UploadFile
import markdown2
from weasyprint import HTML

# 将src目录添加到系统路径
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.workflow import execute_comparison_workflow, execute_historical_workflow
from .config import settings
from .logger import logger


# --- 核心修改区域：run_analysis_service 函数 ---
# 1. 修改函数签名，不再接收 UploadFile 列表
def run_analysis_service(file_paths: List[str], temp_dir_to_clean: str, analysis_params: Dict):
    """
    核心分析服务（生成器版本）：处理已保存的文件路径，并在结束后清理临时目录。
    """
    # 2. 函数不再自己创建临时目录，而是使用从 api.py 传递过来的目录
    # temp_dir = tempfile.mkdtemp(prefix="data_analysis_")
    request_id = os.path.basename(temp_dir_to_clean)
    logger.info(f"为请求 {request_id} 使用已创建的临时目录: {temp_dir_to_clean}")

    try:
        # 3. 函数不再需要保存文件，直接使用路径列表
        analysis_tasks = [{'file': path} for path in file_paths]
        logger.info(f"已接收 {len(analysis_tasks)} 个文件路径进行处理。")

        # --- 后续的分析逻辑保持不变 ---
        num_tasks = len(analysis_tasks)
        if num_tasks < 2:
            raise ValueError("至少需要提供两个数据源才能进行分析。")

        llm_config = settings.get('llm', {})
        output_config = settings.get('output', {})

        if num_tasks == 2:
            logger.info("启动【双版本高精度比对分析】工作流...")
            yield from execute_comparison_workflow(analysis_tasks, analysis_params, llm_config, output_config)
        else:
            logger.info("启动【多版本历史追溯分析】工作流...")
            yield from execute_historical_workflow(analysis_tasks, analysis_params, llm_config, output_config)

        logger.info(f"请求 {request_id} 分析流已完成。")

    except Exception as e:
        logger.error(f"在分析服务中发生错误: {e}", exc_info=True)
        yield f"\n\n服务器分析服务错误: {e}"
        raise e
    finally:
        # 4. 在 finally 块中，清理由 api.py 创建并传递过来的目录
        if os.path.exists(temp_dir_to_clean):
            shutil.rmtree(temp_dir_to_clean)
            logger.info(f"清理并删除临时目录: {temp_dir_to_clean}")


def run_demo_analysis_service(analysis_params: Dict):
    """
    核心示例分析服务（生成器版本）：读取服务器本地的示例文件，并流式返回工作流的结果。
    """
    try:
        project_root = '/app' if os.path.exists('/.dockerenv') else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        data_folder = os.path.join(project_root, 'data')

        demo_files = [
            os.path.join(data_folder, '省份1_数据v1.xlsx'),
            os.path.join(data_folder, '省份1_数据v2.xlsx'),
            os.path.join(data_folder, '省份1_数据v3.xlsx')
        ]

        for f_path in demo_files:
            if not os.path.exists(f_path):
                logger.error(f"示例文件未找到: {f_path}")
                raise FileNotFoundError(f"配置的示例文件未在服务器上找到: {os.path.basename(f_path)}")

        analysis_tasks = [{'file': file_path} for file_path in demo_files]
        logger.info(f"已加载 {len(analysis_tasks)} 个本地示例文件进行分析。")

        llm_config = settings.get('llm', {})
        output_config = settings.get('output', {})

        # 关键改动：使用 yield from 将生成器传递出去
        yield from execute_historical_workflow(analysis_tasks, analysis_params, llm_config, output_config)

        logger.info("示例分析流已完成。")
    except Exception as e:
        logger.error(f"在示例分析服务中发生错误: {e}", exc_info=True)
        yield f"\n\n服务器示例分析服务错误: {e}"
        raise e

def generate_pdf_service(markdown_content: str) -> str:
    try:
        html_content = markdown2.markdown(markdown_content, extras=["tables", "fenced-code-blocks"])
        html_with_style = f"""
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8">
            <style>
              @page {{ size: A4; margin: 20mm; }}
              html, body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif; color: #222; }}
              body {{ font-size: 12px; line-height: 1.6; }}
              h1, h2, h3 {{ color: #333; margin: 0 0 8px 0; }}
              h1 {{ font-size: 22px; }}
              h2 {{ font-size: 18px; }}
              h3 {{ font-size: 14px; }}
              table {{ width: 100%; border-collapse: collapse; border-spacing: 0; table-layout: auto; margin: 8px 0 16px 0; font-size: 12px; }}
              thead {{ background: #f5f5f5; display: table-header-group; }}
              tr {{ page-break-inside: avoid; }}
              th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; text-align: left; word-wrap: break-word; white-space: pre-wrap; page-break-inside: avoid; }}
              .table-wrapper {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
              pre {{ background: #f6f8fa; padding: 10px; border-radius: 4px; overflow: auto; }}
              code {{ background: #f6f8fa; padding: 2px 4px; border-radius: 4px; }}
              @media print {{ body {{ -webkit-print-color-adjust: exact; }} }}
            </style>
          </head>
          <body><div class="table-wrapper">{html_content}</div></body>
        </html>
        """
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="report_") as tmpf:
            pdf_path = tmpf.name
        HTML(string=html_with_style).write_pdf(pdf_path)
        logger.info(f"PDF 生成成功: {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.exception("PDF 生成失败")
        raise