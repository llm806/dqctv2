# backend/app/api.py
import os
import json # 新增: 导入json库用于解析参数
from typing import List
# 新增: 从fastapi导入Form，用于接收表单字段
from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse

from .services import run_analysis_service, generate_pdf_service
from .logger import logger

router = APIRouter()

# cleanup_file 函数无需修改，保持原样
def cleanup_file(path: str):
    """后台任务，用于删除临时文件。"""
    try:
        os.remove(path)
        logger.info(f"已清理临时文件: {path}")
    except OSError as e:
        logger.error(f"清理文件 {path} 失败: {e}")

# 优化: 更新 /analyze 端点以接收动态参数
@router.post("/analyze")
async def analyze_files_endpoint(
    # FastAPI可以智能处理 multipart/form-data 请求
    # files 字段会被识别为文件上传
    files: List[UploadFile],
    # 新增: 使用 Form() 来声明这是一个表单字段
    # 前端发送的 'params' JSON字符串将被这个变量接收
    params: str = Form(...)
):
    if not files or len(files) < 2:
        raise HTTPException(status_code=400, detail="请至少上传两个文件。")

    try:
        # 新增: 将接收到的JSON字符串解析为Python字典
        analysis_params = json.loads(params)

        # 优化: 将解析后的参数字典传递给核心服务函数
        # (请确保 run_analysis_service 函数也已更新以接收此参数)
        report = run_analysis_service(files, analysis_params)

        return {"success": True, "report": report}
    except json.JSONDecodeError:
        # 新增: 健壮性处理，如果前端发送的不是合法的JSON字符串
        raise HTTPException(status_code=400, detail="提供的分析参数格式错误。")
    except Exception as e:
        logger.error(f"分析端点发生未捕获的异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


# /download/pdf 端点无需修改，保持原样
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