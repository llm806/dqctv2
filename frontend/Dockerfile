# frontend/Dockerfile

FROM node:22-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .


# 安装 dos2unix 并转换所有脚本
RUN apk add --no-cache dos2unix && \
    find . -type f -exec dos2unix {} +


# 执行构建命令，生成静态文件到 /app/dist 目录
RUN npm run build

FROM nginx:stable-alpine

# 将构建好的静态文件复制到Nginx的Web服务器根目录
COPY --from=builder /app/dist /usr/share/nginx/html

RUN rm /etc/nginx/conf.d/default.conf

COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 80;

    client_max_body_size 100M;

    # 托管Vue应用的静态文件
    location / {
        root   /usr/share/nginx/html;
        index  index.html;
        try_files $uri $uri/ /index.html;
    }

    # 将所有/api开头的请求代理到"backend"的服务
    location /api {
        proxy_pass http://backend:8000;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding on;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

# 声明Nginx将监听80端口
EXPOSE 80