"""
logger封装
"""
import logging
import os
import shutil
import sys
from datetime import datetime

from loguru import logger

# 移除所有默认的处理器
logger.remove()
logger.bind()

# 自定义格式并添加到标准输出
# log_format = "<g>{time:MM-DD HH:mm:ss}</g> <lvl>{level:<9}</lvl>| {file}:{line} | {message}"
log_format = "<g>{time:MM-DD HH:mm:ss}</g> <lvl>{level:<9}</lvl> \n{message}"
logger.add(sys.stdout, level="INFO", format=log_format, backtrace=True, diagnose=True)


def configure_logging():
    log_file = 'logs/api.log'
    _logger = logging.getLogger('xxx')
    _logger.setLevel(logging.INFO)
    handel_format = '%(asctime)s - %(levelname)s - %(message)s'
    # 设置 propagate 为 False
    # propagate 用于控制日志消息的传播行为，如果设置为 True（默认值），那么该 _logger 记录的消息会向上层的 _logger 传播，导致记录两次日志。
    _logger.propagate = False
    # 移除现有的处理器（防止重复）
    if _logger.hasHandlers():
        _logger.handlers.clear()
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    # 设置日志格式
    formatter = logging.Formatter(handel_format)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    # 添加处理器到日志记录器
    _logger.addHandler(console_handler)
    # _logger.addHandler(file_handler)
    # 打印初始化成功的日志
    _logger.info("Logging configured successfully for 'xxx' _logger.")
    return _logger

def setup_logger(log_type="console_file", log_file="logs/api.log", console_level="INFO", file_level="DEBUG"):
    # 获取数值级别，方便在过滤器中使用
    logger.remove()
    rename_file(log_file)
    console_level_no = logger.level(console_level).no
    file_level_no = logger.level(file_level).no
    if log_type in ("console", "console_file"):
        logger.add(sys.stdout, level=console_level, format=log_format, backtrace=True, diagnose=True,
                   filter=lambda record: console_level_no <= record["level"].no != file_level_no)
    if log_type in ("file", "console_file"):
        logger.add(log_file, encoding="utf-8", level=file_level, format=log_format, backtrace=True, diagnose=True,
                   filter=lambda record: file_level_no <= record["level"].no != console_level_no)
    # else:
    #     logger.add(sys.stdout, level=console_level, format=log_format, backtrace=True, diagnose=True,
    #                filter=lambda record: console_level_no <= record["level"].no != file_level_no)
    #     logger.add(log_file, level=file_level, format=log_format, backtrace=True, diagnose=True,
    #                filter=lambda record: file_level_no <= record["level"].no != console_level_no)
    if "console" in log_type:
        logger.log(console_level,
               f"Console logging configured successfully with level '{console_level}' to 'sys.stdout'.")
    if "file" in log_type:
        logger.log(file_level_no,
               f"File logging configured successfully with level '{file_level}' to '{log_file}'.")
    return logger

def get_logger():
    return logger

def rename_file(ori_path='logs/api.log'):
    new_path = ori_path
    # 检查文件是否存在
    if os.path.exists(ori_path):
        # 获取文件的目录和文件名
        ori_dir = os.path.dirname(ori_path)
        ori_file = os.path.basename(ori_path)

        # 获取文件的创建时间
        creation_time = os.path.getctime(ori_path)
        # 将创建时间格式化为字符串
        formatted_time = datetime.fromtimestamp(creation_time).strftime("%Y%m%d_%H%M%S")
        # 构建新的文件路径
        new_path = os.path.join(ori_dir, f'{formatted_time}_{ori_file}')
        shutil.copy2(ori_path, new_path)
        # 删除旧文件
        os.remove(ori_path)
    return ori_path, new_path

