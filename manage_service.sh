#!/bin/bash

# 服务管理脚本
SERVICE_NAME="OpenAPI"
PID_FILE="/tmp/${SERVICE_NAME}.pid"
LOG_FILE="output.log"
PYTHON_PATH="/opt/anaconda3/envs/oa/bin/python"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# 设置模块查找路径为项目根目录
export PYTHONPATH="$SCRIPT_DIR"

start_service() {
    # 检查是否已有同名进程（即使PID文件丢失）
    EXISTING_PID=$(pgrep -f "${PYTHON_PATH}.*main.py")
    if [ -n "$EXISTING_PID" ]; then
        echo "Conflict: Process already running (PID: $EXISTING_PID). Use 'stop' first."
        return 1
    fi
    
    if [ -f "$PID_FILE" ]; then
        if ps -p "$(cat "$PID_FILE")" > /dev/null; then
            echo "Service is already running (PID: $(cat $PID_FILE))"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi

    echo "Starting ${SERVICE_NAME}..."
    # 构造要运行的命令字符串
    SHELL_CMD="nohup $PYTHON_PATH \"$SCRIPT_DIR/app/main.py\" > \"$SCRIPT_DIR/$LOG_FILE\" 2>&1 &"
    echo "$SHELL_CMD"
    eval "$SHELL_CMD"
    echo $! > "$PID_FILE"
    echo "Service started (PID: $(cat $PID_FILE))"
}

stop_service() {
    if [ ! -f "$PID_FILE" ]; then
        echo "PID file not found. Service may not be running."
        return 1
    fi

    PID=$(cat "$PID_FILE")
    if ! ps -p "$PID" > /dev/null; then
        echo "Service not running (PID: "$PID")"
        rm -f "$PID_FILE"
        return 1
    fi

    echo "Stopping ${SERVICE_NAME} (PID: "$PID")..."
    kill -TERM "$PID"
    sleep 2  # 等待进程响应TERM信号

    if ps -p "$PID" > /dev/null; then
        echo "Process still alive, sending SIGKILL..."
        kill -9 "$PID"  # 强制终止
        sleep 1
    fi

    if ! ps -p "$PID" > /dev/null; then
      rm -f "$PID_FILE"
      echo "Service stopped"
    else
      echo "ERROR!!!Failed to stop service (PID: "$PID")"
    fi
}

check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null; then
            echo "Service is running (PID: "$PID")"
            return 0
        else
            echo "PID file exists but service is not running"
            return 1
        fi
    else
        echo "Service is not running"
        return 1
    fi
}

case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        sleep 2
        start_service
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0