FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件以利用 Docker 缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码
COPY . .

# 创建上传目录
RUN mkdir -p uploads logs

EXPOSE 5001

CMD ["python", "run.py"]
