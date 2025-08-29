# backend/app/services.py
import os
import shutil
import tempfile  # 导入标准库
from typing import List
from fastapi import UploadFile
import markdown2
from weasyprint import HTML

# 将src目录添加到系统路径
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.workflow import execute_comparison_workflow, execute_historical_workflow
from .config import settings
from .logger import logger


def run_analysis_service(files: List[UploadFile]) -> str:
    """
    核心分析服务：在系统临时目录中处理上传的文件，运行工作流，并自动清理。
    """
    # 使用 tempfile.mkdtemp() 在操作系统的临时区域创建唯一的目录
    temp_dir = tempfile.mkdtemp(prefix="data_analysis_")
    request_id = os.path.basename(temp_dir)
    logger.info(f"为请求 {request_id} 创建系统临时目录: {temp_dir}")

    try:
        analysis_tasks = []
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            analysis_tasks.append({'file': file_path})

        logger.info(f"文件已临时保存，任务数: {len(analysis_tasks)}")

        num_tasks = len(analysis_tasks)
        if num_tasks < 2:
            raise ValueError("至少需要提供两个数据源才能进行分析。")

        if num_tasks == 2:
            logger.info("启动【双版本高精度比对分析】工作流...")
            report = execute_comparison_workflow(analysis_tasks, settings)
        else:
            logger.info("启动【多版本历史追溯分析】工作流...")
            report = execute_historical_workflow(analysis_tasks, settings)

        logger.info(f"请求 {request_id} 分析完成。")
        return report

    except Exception as e:
        logger.error(f"在分析服务中发生错误: {e}", exc_info=True)
        raise e
    finally:
        # 确保临时目录总是被清理
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"清理并删除系统临时目录: {temp_dir}")


def generate_pdf_service(markdown_content: str) -> str:
    """
    将 Markdown 内容转换为 PDF，使用 markdown2 支持 tables 扩展，
    并注入针对 WeasyPrint 的表格样式（表头跨页、单元格换行、边框等）。
    返回生成的 PDF 临时文件路径。
    """
    try:
        # 使用 markdown2 的 extras，确保表格语法被解析为 <table>
        # 其他可选 extras: "fenced-code-blocks", "strike", "tables", "cuddled-lists", "smarty"
        html_content = markdown2.markdown(markdown_content, extras=["tables", "fenced-code-blocks"])

        # 强力 CSS：表格边框、表头跨页重复、单元格换行、避免分页中间断行等
        # 根据需要可以调整字体族以保证中文显示（此处示例包含常见中文字体回退）
        html_with_style = f"""
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8">
            <style>
              /* 基本字体与排版 */
              @page {{ size: A4; margin: 20mm; }}
              html, body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif; color: #222; }}
              body {{ font-size: 12px; line-height: 1.6; }}

              /* 标题 */
              h1, h2, h3 {{ color: #333; margin: 0 0 8px 0; }}
              h1 {{ font-size: 22px; }}
              h2 {{ font-size: 18px; }}
              h3 {{ font-size: 14px; }}

              /* 表格基础样式 */
              table {{
                width: 100%;
                border-collapse: collapse;
                border-spacing: 0;
                table-layout: auto; /* 若希望固定列宽可改为 fixed */
                margin: 8px 0 16px 0;
                font-size: 12px;
              }}
              thead {{ background: #f5f5f5; }}
              th, td {{
                border: 1px solid #ddd;
                padding: 6px 8px;
                vertical-align: top;
                text-align: left;
                word-wrap: break-word;      /* 长单词换行 */
                white-space: pre-wrap;      /* 保留换行并允许换行 */
              }}

              /* 保证表头在分页时重复（WeasyPrint 会遵守 display: table-header-group）*/
              thead {{ display: table-header-group; }}

              /* 避免 tr 在分页中被拆开（尽量不拆一行到两页） */
              tr {{ page-break-inside: avoid; }}

              /* 当列过多时允许水平滚动（可选：若希望页面内缩小请移除此规则并用 table-layout: fixed） */
              .table-wrapper {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }}

              /* 代码块 */
              pre {{ background: #f6f8fa; padding: 10px; border-radius: 4px; overflow: auto; }}
              code {{ background: #f6f8fa; padding: 2px 4px; border-radius: 4px; }}

              /* 防止在单元格内出现不希望的断页 */
              td, th {{ page-break-inside: avoid; }}

              /* 小屏或长表格可微调字体 */
              @media print {{
                body {{ -webkit-print-color-adjust: exact; }}
              }}
            </style>
          </head>
          <body>
            <!-- 为避免超宽表格被截断，包一层 div 允许横向滚动（WeasyPrint 会导出可滚动区域的内容） -->
            <div class="table-wrapper">
              {html_content}
            </div>
          </body>
        </html>
        """

        # 生成临时 PDF 文件
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="report_") as tmpf:
            pdf_path = tmpf.name

        HTML(string=html_with_style).write_pdf(pdf_path)
        logger.info(f"PDF 生成成功: {pdf_path}")
        return pdf_path

    except Exception as e:
        logger.exception("PDF 生成失败")
        raise
