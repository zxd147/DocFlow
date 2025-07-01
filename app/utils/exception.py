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
    code, status = -1, 500
    if isinstance(exc, json.JSONDecodeError):
        error_msg = (
            f"JSON解析失败: {exc.msg}\n"
            f"错误位置: 第{exc.lineno}行第{exc.colno}列 (字符{exc.pos})\n"
            f"原始数据: [{exc.doc}]"  # 这里会输出原始 JSON 字符串
        )
        message = f"{caller_name}: {exc_type}: {error_msg}"
    else:
        message = f"{caller_name}: {exc_type}: {exc}"
        logger.error(message)
    return code, status, message

def single_exception(exc):
    # 获取调用栈信息（跳过当前帧）
    status = 500
    if isinstance(exc, SigIntException):
        message = f"SigIntException occurred: {str(exc)}"
        graceful_shutdown(signal.SIGINT)
        code = 0
    elif isinstance(exc, SigTermException):
        message = f"SigTermException occurred: {str(exc)}"
        graceful_shutdown(signal.SIGTERM)
        code = 0
    elif isinstance(exc, ShutdownSignalException):
        message = f"ShutdownSignalException occurred: {str(exc)}"
        graceful_shutdown()
        code = 1
    elif isinstance(exc, asyncio.CancelledError):
        message = f"Task cancelled successfully: {str(exc)}"
        graceful_shutdown()
        code = 1
    else:
        message = f"OtherError occurred: {str(exc)}"
        graceful_shutdown()
        code = -1
    return code, status, message

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
    elif isinstance(exc, ValueError):
        status = 400
    elif isinstance(exc, TimeoutError):
        status = 408
    else:
        status = 500
    return code, status, message



