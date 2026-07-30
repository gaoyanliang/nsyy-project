#!/bin/bash
# 开机自启动脚本 - 用于 /home/gyl/gyl_server 下使用 conda gg 环境启动两个 Python 服务

# 等系统基本稳定
sleep 10

# 防止重复启动
if pgrep -f "main:app" >/dev/null; then
    exit 0
fi

# 设置工作目录
PROJECT_DIR="/home/gyl/gyl_server"
cd "$PROJECT_DIR" || { echo "错误：目录 $PROJECT_DIR 不存在"; exit 1; }

# 定义 Conda 环境 Python 的绝对路径（请根据实际情况确认）
PYTHON_BIN="/home/gyl/.conda/envs/gg/bin/python"

# 等待端口监听的函数（使用 ss）
wait_for_port_listen() {
    local port=$1
    local timeout=$2
    local service_name=$3
    local count=0
    echo "等待 $service_name 启动（端口 $port）..."
    while ! ss -lnt | grep -q ":${port} "; do
        sleep 1
        count=$((count + 1))
        if [ $count -ge $timeout ]; then
            echo "错误：等待 $service_name 超时（${timeout}秒），端口 $port 未监听"
            exit 1
        fi
    done
    echo "$service_name 已就绪。"
}

# ---------- 等待 MySQL 就绪（检测 3306 端口） ----------
wait_for_port_listen 3306 30 "MySQL"
# ---------- 等待 Redis 就绪（检测 6379 端口） ----------
wait_for_port_listen 6379 30 "Redis"


# === 启动前滚动日志 ===
if [ -f nohup.log ]; then
    mv nohup.log "nohup_$(date +'%Y%m%d_%H%M%S').log"
fi
if [ -f nohup_mz.log ]; then
    mv nohup_mz.log "nohup_mz_$(date +'%Y%m%d_%H%M%S').log"
fi

# === 启动前滚动日志 ===
if [ -f my_app.log ]; then
    mv my_app.log "my_app_$(date +'%Y%m%d_%H%M%S').log"
fi
if [ -f mz.log ]; then
    mv mz.log "mz_$(date +'%Y%m%d_%H%M%S').log"
fi


# ---------- 启动第一个服务 (fastapi) ----------
echo "启动 main_gyl.py ..."
nohup $PYTHON_BIN -u ./main_gyl.py >> nohup.log 2>&1 &
echo "main_gyl 服务已启动，等待 5 秒后启动下一个服务..."
sleep 5

# ---------- 启动第二个服务 (main) ----------
echo "启动 main_mz.py ..."
nohup $PYTHON_BIN -u ./main_mz.py >> nohup_mz.log 2>&1 &
echo "main_mz 服务已启动。"

echo "所有服务启动完成。"