# backend/Dockerfile

FROM python:3.11-slim

# 安装 weasyprint 所需的系统依赖库
# 这对于 Debian 系的 python:3.11-slim 镜像是兼容的
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libpangoft2-1.0-0 \
    libfontconfig1 \
    fonts-wqy-zenhei \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 设置容器内的工作目录
WORKDIR /app

# 现在路径需要相对于项目根目录
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 分别将 backend 和 src 目录复制到镜像中
COPY backend/ .
COPY src/ ./src/

# 声明服务将监听8000端口
EXPOSE 8000

# 容器启动时运行的命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]