# --- 构建阶段 ---
FROM node:22-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# 执行构建命令，生成静态文件到 /app/dist 目录
RUN npm run build

# --- 生产阶段 ---
FROM nginx:stable-alpine

# 将构建好的静态文件复制到Nginx的Web服务器根目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 移除Nginx的默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 【优雅实现】直接在Dockerfile中创建新的Nginx配置文件
# 这样做的好处是前端配置完全自包含，无需外部nginx.conf文件
COPY <<EOF /etc/nginx/conf.d/default.conf
server {
    listen 80;

    # 托管Vue应用的静态文件
    location / {
        root   /usr/share/nginx/html;
        index  index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # 将所有/api开头的请求代理到名为"backend"的服务
    # backend这个主机名由docker-compose定义
    location /api {
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        proxy_pass http://backend:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# 声明Nginx将监听80端口
EXPOSE 80