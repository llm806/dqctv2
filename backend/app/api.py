# backend/app/api.py

import os
import json
import tempfile  # 导入 tempfile
import shutil    # 导入 shutil
from typing import List, Dict
from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, StreamingResponse

from .services import run_analysis_service, generate_pdf_service, run_demo_analysis_service
from .logger import logger

# ... (cleanup_file 和 router 定义保持不变) ...
router = APIRouter()
def cleanup_file(path: str):
    """后台任务，用于删除临时文件。"""
    try:
        os.remove(path)
        logger.info(f"已清理临时文件: {path}")
    except OSError as e:
        logger.error(f"清理文件 {path} 失败: {e}")

@router.post("/analyze")
async def analyze_files_endpoint(
    files: List[UploadFile],
    params: str = Form(...)
):
    if not files or len(files) < 2:
        raise HTTPException(status_code=400, detail="请至少上传两个文件。")

    # --- 核心修改区域 ---
    # 1. 在端点函数内部立即创建我们自己的临时目录
    temp_dir = tempfile.mkdtemp(prefix="api_temp_upload_")
    file_paths = []

    try:
        # 2. 立即读取并保存所有上传的文件
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            # 使用 await file.read() 异步读取文件内容
            file_content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            file_paths.append(file_path)

        analysis_params = json.loads(params)

        # 3. 将新保存的文件路径和临时目录路径，传递给服务生成器
        #    注意：这里我们不再传递 UploadFile 对象列表
        report_generator = run_analysis_service(file_paths, temp_dir, analysis_params)

        return StreamingResponse(report_generator, media_type="text/plain; charset=utf-8")

    except json.JSONDecodeError:
        # 如果在解析参数时出错，也要清理临时目录
        shutil.rmtree(temp_dir)
        raise HTTPException(status_code=400, detail="提供的分析参数格式错误。")
    except Exception as e:
        # 如果在保存文件等步骤出错，也要清理
        shutil.rmtree(temp_dir)
        logger.error(f"分析端点发生未捕获的异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# ... (analyze_demo_endpoint 和 download_pdf_endpoint 保持不变，因为它们不处理文件上传) ...
@router.post("/analyze-demo")
async def analyze_demo_endpoint(analysis_params: Dict):
    """
    处理来自前端的示例分析请求，并以流式方式返回报告。
    """
    try:
        if not analysis_params:
            raise HTTPException(status_code=400, detail="未提供分析参数。")

        # run_demo_analysis_service 现在也是一个生成器函数
        report_generator = run_demo_analysis_service(analysis_params)
        # 以流式响应的方式返回生成器内容
        return StreamingResponse(report_generator, media_type="text/plain; charset=utf-8")
    except FileNotFoundError as e:
        logger.error(f"示例文件未找到: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"示例分析端点发生未捕获的异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.post("/download/pdf")
async def download_pdf_endpoint(data: dict, background_tasks: BackgroundTasks):
    """
    处理PDF下载请求（此部分功能保持不变）。
    """
    markdown_content = data.get('markdown')
    if not markdown_content:
        raise HTTPException(status_code=400, detail="未提供Markdown内容。")

    try:
        pdf_path = generate_pdf_service(markdown_content)
        background_tasks.add_task(cleanup_file, pdf_path)
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename='analysis_report.pdf'
        )
    except Exception as e:
        logger.error(f"PDF下载端点发生错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成PDF报告时出错: {str(e)}")