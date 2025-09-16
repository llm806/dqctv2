# backend/app/services.py
import os
import shutil
import tempfile
# 优化: 导入 Dict 类型提示以增强代码可读性
from typing import List, Dict
from fastapi import UploadFile
import markdown2
from weasyprint import HTML

# 将src目录添加到系统路径 (保持不变)
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.workflow import execute_comparison_workflow, execute_historical_workflow
from .config import settings
from .logger import logger

# 更新函数以接收来自API层的动态分析参数
def run_analysis_service(files: List[UploadFile], analysis_params: Dict) -> str:
    """
    核心分析服务：在系统临时目录中处理上传的文件，运行工作流，并自动清理。

    Args:
        files: 用户上传的文件列表。
        analysis_params: 一个包含本次分析所需参数的字典，
                         例如：{'keyColumns': ['列A', '列B'], 'valueColumn': '列C'}。
    """
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

        # 优化: 不再使用静态的 settings['analysis_params']，
        # 而是将动态的 analysis_params 和静态的 llm/output 配置分别传递给工作流。
        # 这要求下游的 workflow 函数也做出相应修改。
        llm_config = settings.get('llm', {})
        output_config = settings.get('output', {})

        if num_tasks == 2:
            logger.info("启动【双版本高精度比对分析】工作流...")
            report = execute_comparison_workflow(analysis_tasks, analysis_params, llm_config, output_config)
        else:
            logger.info("启动【多版本历史追溯分析】工作流...")
            report = execute_historical_workflow(analysis_tasks, analysis_params, llm_config, output_config)

        logger.info(f"请求 {request_id} 分析完成。")
        return report

    except Exception as e:
        logger.error(f"在分析服务中发生错误: {e}", exc_info=True)
        raise e
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"清理并删除系统临时目录: {temp_dir}")


def generate_pdf_service(markdown_content: str) -> str:
    try:
        html_content = markdown2.markdown(markdown_content, extras=["tables", "fenced-code-blocks"])

        html_with_style = f"""
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8">
            <style>
              /* CSS 样式保持不变 */
              @page {{ size: A4; margin: 20mm; }}
              html, body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif; color: #222; }}
              body {{ font-size: 12px; line-height: 1.6; }}
              h1, h2, h3 {{ color: #333; margin: 0 0 8px 0; }}
              h1 {{ font-size: 22px; }}
              h2 {{ font-size: 18px; }}
              h3 {{ font-size: 14px; }}
              table {{
                width: 100%;
                border-collapse: collapse;
                border-spacing: 0;
                table-layout: auto;
                margin: 8px 0 16px 0;
                font-size: 12px;
              }}
              thead {{ background: #f5f5f5; display: table-header-group; }}
              tr {{ page-break-inside: avoid; }}
              th, td {{
                border: 1px solid #ddd;
                padding: 6px 8px;
                vertical-align: top;
                text-align: left;
                word-wrap: break-word;
                white-space: pre-wrap;
                page-break-inside: avoid;
              }}
              .table-wrapper {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
              pre {{ background: #f6f8fa; padding: 10px; border-radius: 4px; overflow: auto; }}
              code {{ background: #f6f8fa; padding: 2px 4px; border-radius: 4px; }}
              @media print {{
                body {{ -webkit-print-color-adjust: exact; }}
              }}
            </style>
          </head>
          <body>
            <div class="table-wrapper">
              {html_content}
            </div>
          </body>
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

# 示例分析服务函数
def run_demo_analysis_service(analysis_params: Dict) -> str:
    """
    核心示例分析服务：直接读取服务器本地的示例文件，运行工作流。
    """
    try:
        # START: 使用新的、更简单的路径定位方法
        project_root = ''
        # 判断是否在Docker容器中 (一个常用的技巧是检查根目录下是否存在 .dockerenv 文件)
        if os.path.exists('/.dockerenv'):
            # 如果在Docker中，项目根目录就是/app
            project_root = '/app'
        else:
            # 如果在本地运行，则通过相对路径向上回溯两层找到项目根目录
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        data_folder = os.path.join(project_root, 'data')
        # END: 新的路径定位方法

        demo_files = [
            os.path.join(data_folder, '湖北-电量数据v1.xlsx'),
            os.path.join(data_folder, '湖北-电量数据v2.xlsx'),
            os.path.join(data_folder, '湖北-电量数据v3.xlsx')
        ]

        for f_path in demo_files:
            if not os.path.exists(f_path):
                logger.error(f"示例文件未找到: {f_path}")
                raise FileNotFoundError(f"配置的示例文件未在服务器上找到: {os.path.basename(f_path)}")

        analysis_tasks = [{'file': file_path} for file_path in demo_files]
        logger.info(f"已加载 {len(analysis_tasks)} 个本地示例文件进行分析。")

        llm_config = settings.get('llm', {})
        output_config = settings.get('output', {})
        report = execute_historical_workflow(analysis_tasks, analysis_params, llm_config, output_config)

        logger.info("示例分析完成。")
        return report
    except Exception as e:
        logger.error(f"在示例分析服务中发生错误: {e}", exc_info=True)
        raise e