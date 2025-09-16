# backend/app/api.py
import os
import json
# MODIFIED: Import Dict along with List
from typing import List, Dict
from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse

# Import the new demo service function
from .services import run_analysis_service, generate_pdf_service, run_demo_analysis_service
from .logger import logger

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

    try:
        analysis_params = json.loads(params)
        report = run_analysis_service(files, analysis_params)
        return {"success": True, "report": report}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="提供的分析参数格式错误。")
    except Exception as e:
        logger.error(f"分析端点发生未捕获的异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.post("/analyze-demo")
async def analyze_demo_endpoint(analysis_params: Dict):
    """
    处理来自前端的示例分析请求。
    请求体中只包含分析参数，文件路径在服务器端硬编码。
    """
    try:
        if not analysis_params:
            raise HTTPException(status_code=400, detail="未提供分析参数。")

        report = run_demo_analysis_service(analysis_params)
        return {"success": True, "report": report}
    except FileNotFoundError as e:
        logger.error(f"示例文件未找到: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"示例分析端点发生未捕获的异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.post("/download/pdf")
async def download_pdf_endpoint(data: dict, background_tasks: BackgroundTasks):
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