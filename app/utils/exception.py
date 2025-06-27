import asyncio
import inspect
import json
import signal

from app.models.exception_model import SigIntException, SigTermException, ShutdownSignalException
from app.utils.logger import get_logger
from app.utils.status import graceful_shutdown

logger = get_logger()


def llm_exception(exc):
    # 获取调用栈信息（跳过当前帧）
    caller_frame = inspect.stack()[1]
    caller_name = caller_frame.function
    exc_type = type(exc).__name__
    if isinstance(exc, json.JSONDecodeError):
        error_msg = (
            f"JSON解析失败: {exc.msg}\n"
            f"错误位置: 第{exc.lineno}行第{exc.colno}列 (字符{exc.pos})\n"
            f"原始数据: [{exc.doc}]"  # 这里会输出原始 JSON 字符串
        )
        logger.error(f"{caller_name}: {exc_type}: {error_msg}")
    else:
        logger.error(f"{caller_name}: HTTP错误: {exc_type}: {exc}")

def single_exception(exc):
    if isinstance(exc, SigIntException):
        logger.info(f"SigIntException occurred: {str(exc)}")
        graceful_shutdown(signal.SIGINT)
    elif isinstance(exc, SigTermException):
        logger.info(f"SigTermException occurred: {str(exc)}")
        graceful_shutdown(signal.SIGTERM)
    elif isinstance(exc, ShutdownSignalException):
        logger.warning(f"ShutdownSignalException occurred: {str(exc)}")
        graceful_shutdown()
    elif isinstance(exc, asyncio.CancelledError):
        logger.warning(f"Task cancelled successfully: {str(exc)}")
        graceful_shutdown()
    else:
        logger.warning(f"OtherError occurred: {str(exc)}")
        graceful_shutdown()

def file_exception(exc):
    # 获取调用栈信息（跳过当前帧）
    caller_frame = inspect.stack()[1]
    caller_name = caller_frame.function
    exc_type = type(exc).__name__
    code = -1
    message = f"{caller_name}: {exc_type}: {exc}"
    if isinstance(exc, json.JSONDecodeError):
        error_msg = (
            f"JSON解析失败: {exc.msg}\n"
            f"错误位置: 第{exc.lineno}行第{exc.colno}列 (字符{exc.pos})\n"
            f"原始数据: [{exc.doc}]"  # 这里会输出原始 JSON 字符串
        )
        message = f"{caller_name}: {exc_type}: {error_msg}"
        status = 400
        return code, status, message
    elif isinstance(exc, ValueError):
        status = 400
        return code, status, message
    elif isinstance(exc, TimeoutError):
        status = 408
        return code, status, message
    else:
        status = 500
        return code, status, message



