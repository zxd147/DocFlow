from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI

from app.services.clients import init_client
from app.utils.logger import setup_logger, get_logger


@asynccontextmanager
async def lifespan(init_app: FastAPI):
    setup_logger("console")
    logger = get_logger()
    # 初始化客户端（启动阶段）
    wechat_mp, feishu_bot = await init_client()
    init_app.state.wechat_mp = wechat_mp
    init_app.state.feishu_bot = feishu_bot
    logger.info("Successfully mounted clients: WeChat MP and Feishu Robot")  # 合并日志
    # 记录启动时间
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"Application started at {start_time}")
    try:
        yield
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        logger.warning("Application shutting down, starting cleanup...")
        # 关闭客户端（关闭阶段）
        await init_app.state.feishu_bot.async_terminate()
        logger.info("All clients closed successfully: WeChat MP and Feishu Robot")  # 合并日志
        # 记录关闭时间并清理日志
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Shutting down at {end_time} | Uptime: {datetime.now() - datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')}")
        logger.remove()