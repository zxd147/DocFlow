from datetime import datetime

from fastapi import Request

from app.utils.logger import get_logger

logger = get_logger()

async def log_request_middleware(request: Request, call_next):
    """仅记录请求路径的简化中间件"""
    request_id = datetime.now().timestamp()  # 使用datetime获取时间戳
    path = request.url.path
    method = request.method
    # 只记录基本信息
    logger.info(f"[{request_id}] {method} {path}")
    # 直接转发到下一个处理器
    response = await call_next(request)
    # 记录响应状态
    logger.info(f"[{request_id}] Response: {response.status_code}")
    return response