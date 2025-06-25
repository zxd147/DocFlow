import asyncio
import signal
import sys
import time

import GPUtil
import psutil

from app.models.exception_model import SigIntException, SigTermException, ShutdownSignalException
from app.utils.logger import get_logger
from app.utils.loop import get_loop

logger = get_logger()

def get_system_status():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    memory_total = f"{memory_info.total / (1024 ** 3):.2f} GB"
    memory_available = f"{memory_info.available / (1024 ** 3):.2f} GB"
    memory_used = f"{memory_info.used / (1024 ** 3):.2f} GB"
    memory_percent = memory_info.percent
    gpuInfo = []
    devices = ["cpu", "cuda:0"]
    gpus = GPUtil.getGPUs()
    for gpu in gpus:
        gpuInfo.append(
            {
                "gpu_id": gpu.id,
                "gpu_load": f"{gpu.load}%",
                "gpu_memory": {
                    "total_MB": f"{gpu.memoryTotal} MiB",
                    "total_GB": f"{gpu.memoryTotal / 1024:.2f} GiB",
                    "used": f"{gpu.memoryUsed} MiB",
                    "free": f"{gpu.memoryFree} MiB"
                }
            }
        )
    status_data = {
        "devices": devices,
        "cpu_percent": cpu_percent,
        "memory_total": memory_total,
        "memory_available": memory_available,
        "memory_used": memory_used,
        "memory_percent": memory_percent,
        "gpu": gpuInfo,
    }
    return status_data

def keep_alive():
    while True:
        time.sleep(3600)

async def async_keep_alive():
    while True:
        await asyncio.sleep(3600)

def graceful_shutdown(signum=None, frame=None):
    """信号驱动的优雅退出"""
    loop = get_loop()
    if hasattr(graceful_shutdown, "_is_cleaned"):  # 防止重复调用
        return
    if loop.is_running() and not hasattr(graceful_shutdown, "_is_raised"):  # 处理异步任务
        graceful_shutdown._is_raised = True
        # 根据信号类型抛出对应的自定义异常
        if signum == signal.SIGINT:
            raise SigIntException("RuntimeError: Received SIGINT")
        elif signum == signal.SIGTERM:
            raise SigTermException("RuntimeError: Received SIGTERM")
        else:
            raise ShutdownSignalException("RuntimeError: Unknown shutdown signal received.")
    logger.info(f"Received signal {signum or 'exception'}, shutting down...")
    if hasattr(graceful_shutdown, 'task') and not graceful_shutdown.task.done():
        graceful_shutdown.task.cancel()  # 取消任务
        try:
            loop.run_until_complete(graceful_shutdown.task)
            logger.info("Task is done, no need to cancel")
        except asyncio.CancelledError:
            logger.info("Task cancelled successfully")
    # 执行非异步的清理逻辑（如关闭文件、数据库连接等）
    if hasattr(graceful_shutdown, 'feishu_bot'):
        logger.info("Releasing Feishu resources...")
        # 直接释放关键资源（根据实际需求调整）
        graceful_shutdown.feishu_bot.terminate()
        del graceful_shutdown.feishu_bot
    graceful_shutdown._is_cleaned = True  # 加标记
    exit_code = 0 if signum in (signal.SIGINT, signal.SIGTERM) else 1
    logger.info(f"Service terminated, will exit with code {exit_code}.")
    sys.exit(exit_code)

