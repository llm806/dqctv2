# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as api_router
from app.logger import logger

app = FastAPI(
    title="Data Analysis LLM Agent API",
    description="一个由LLM驱动的数据分析Agent后端服务",
    version="1.0.0"
)

# 配置CORS
# 注意：在生产环境中，应将 allow_origins 限制为你的前端域名
origins = [
    "http://localhost:5173", # Vite 默认开发服务器地址
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Health Check"])
async def read_root():
    logger.info("Health check endpoint was hit.")
    return {"status": "ok", "message": "Welcome to the Data Analysis LLM Agent API!"}