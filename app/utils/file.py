import asyncio
import base64
import mimetypes
import os
import re
import shutil
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Union, BinaryIO, Tuple
from urllib.parse import unquote

import aiofiles
import httpx
from fastapi import UploadFile, HTTPException

from app.utils.logger import get_logger

logger = get_logger()
mime_extension_map = {
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/html": ".html",
    "text/csv": ".csv",
    "text/css": ".css",
    "text/javascript": ".js",
    "application/json": ".json",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/xml": ".xml",
    "application/javascript": ".js",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/x-icon": ".ico",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",  # 这里加上 wav
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    # 还可以继续补充
}
timestamp_format_map = {
    "null": None,
    "full": "%Y%m%d_%H%M%S",
    "date": "%Y%m%d",
    "time": "%H%M%S",
    "year": "%Y",
    "month": "%m",
    "day": "%d",
    "hour": "%H",
    "minute": "%M",
    "second": "%S",
}
# 反向映射：后缀 => MIME
extension_mime_map = {v: k for k, v in mime_extension_map.items()}

def get_full_path(default_dir, path, name, extension, st_fmt="null"):
    has_ext = bool(os.path.splitext(path)[1])
    # 检查路径是否为完整路径
    if os.path.isabs(path):
        # 检查是否有文件后缀
        if has_ext and os.path.exists(os.path.dirname(path)):
            # 这是一个完整路径且父目录存在
            final_path = path
        elif os.path.isdir(path):
            # 这是一个存在的完整目录
            final_path = os.path.join(path, name + extension)
        else:
            # 路径不存在或者不合法
            logs = f"Invalid path provided, {path}"
            logger.error(logs)
            raise ValueError(logs)
    elif path.find('/') == -1:
        # 不存在路径分隔符
        if has_ext:
            # 这是一个带后缀的文件名
            final_path = os.path.join(default_dir, path)
        elif path == '':
            final_path = os.path.join(default_dir, name + extension)
        else:
            # 没有后缀名的文件名
            final_path = os.path.join(default_dir, path + extension)
    else:
        if '/' in path and os.path.isdir(
                os.path.dirname(path) if has_ext else path):
            # 不是绝对路径但包含路径分隔符且存在, 这是一个相对目录
            logs = f"Warning: {path}, 相对路径仅供测试, 请使用绝对路径"
            logger.warning(logs)
            if has_ext:
                final_path = os.path.abspath(path)
            else:
                # path = str(os.path.join(path, name + extension))
                path = os.path.join(path, f"{name}{extension}")
                final_path = os.path.abspath(path)
        else:
            # 路径不存在或者不合法
            logs = f"Invalid path provided, {path}"
            logger.error(logs)
            raise ValueError(logs)
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    final_path = add_timestamp_to_filepath(final_path, fmt=st_fmt)
    return final_path

def add_timestamp_to_filepath(path: str, fmt: str = "null") -> str:
    fmt_str = timestamp_format_map.get(fmt, "%Y%m%d_%H%M%S")
    if not fmt_str:
        return path
    timestamp_str = datetime.now().strftime(fmt_str)
    p = Path(path)
    new_name = f"{p.stem}[{timestamp_str}]{p.suffix}"
    new_path = str(p.with_name(new_name))
    return new_path

def get_extension_from_mime(content_type: str) -> str:
    extension = mime_extension_map.get(content_type) or mimetypes.guess_extension(content_type, strict=False) or ""
    return extension

def get_mime_from_extension(extension: str) -> str:
    extension = "." + extension if not extension.startswith(".") else extension
    mime = extension_mime_map.get(extension.lower()) or mimetypes.guess_type("file" + extension, strict=False)[0] or ""
    return mime

async def async_get_bytes_from_file(file: UploadFile) -> Tuple[bytes, int, str]:
    contents = await file.read()
    size = len(contents)
    extension = get_extension_from_mime(file.content_type or "")
    return contents, size, extension

def get_bytes_from_file(file: UploadFile) -> Tuple[bytes, int, str]:
    contents = file.file.read()  # 直接使用 `UploadFile` 的文件对象
    size = len(contents)
    extension = get_extension_from_mime(file.content_type or "")
    return contents, size, extension

def get_file_like_from_file(file: UploadFile) -> Tuple[BinaryIO, int, str]:
    contents = file.file  # 直接使用 `UploadFile` 的文件对象
    contents.seek(0, 2)  # 移动到文件末尾
    source_size = contents.tell()  # 获取当前位置，即文件大小
    contents.seek(0)  # 将指针重置到文件开头
    extension = get_extension_from_mime(file.content_type or "")
    return contents, source_size, extension

async def async_get_bytes_from_path(path: str) -> Tuple[bytes, int]:
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    async with aiofiles.open(path, "rb") as f:
        contents = await f.read()
        size = len(contents)
    return contents, size

def get_bytes_from_path(path: str) -> Tuple[bytes, int]:
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(path, "rb") as f:
        contents = f.read()
        size = len(contents)
    return contents, size

async def get_bytes_from_url(url: str) -> Tuple[bytes, int, str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        contents = response.content  # 直接使用 `httpx.Response` 的内容对象
        content_type = response.headers.get("content-type", "")
    size = len(contents)
    extension = get_extension_from_mime(content_type)
    return contents, size, extension

def get_bytes_from_base64(base64_str: str) -> Tuple[bytes, int, str]:
    extension = ''
    if base64_str.startswith("data:"):
        # 使用正则表达式提取文件格式
        match = re.match(r'data:(.*?);base64,(.*)', base64_str)
        if match:
            content_type = match.group(1)
            extension = get_extension_from_mime(content_type)
            base64_str = match.group(2)
    contents = base64.b64decode(base64_str)
    size = len(contents)
    return contents, size, extension

# def ensure_file_like(obj: Union[bytes, BinaryIO]) -> BinaryIO:
#     if isinstance(obj, bytes):
#         return BytesIO(obj)
#     return obj  # already file-like
#
# def ensure_bytes(obj: Union[bytes, BinaryIO]) -> bytes:
#     if isinstance(obj, bytes):
#         return obj
#     return obj.read()
#

def to_bytesio(obj: Union[str, bytes, BinaryIO], encoding="utf-8") -> BytesIO:
    if isinstance(obj, BytesIO):
        return obj
    elif isinstance(obj, bytes):
        return BytesIO(obj)
    elif isinstance(obj, str):
        return BytesIO(obj.encode(encoding))
    elif hasattr(obj, "read") and callable(obj.read):
        try:
            obj.seek(0)
        except Exception:
            pass
        return BytesIO(obj.read())
    else:
        raise TypeError(f"Unsupported type: {type(obj)} for to_bytesio")

def to_bytes(obj: Union[str, bytes, BinaryIO], encoding="utf-8") -> bytes:
    if isinstance(obj, BytesIO):
        return obj.getvalue()  # 更保险
    elif isinstance(obj, bytes):
        return obj
    elif isinstance(obj, str):
        return obj.encode(encoding)
    elif hasattr(obj, "read") and callable(obj.read):
        try:
            obj.seek(0)
        except Exception:
            pass
        return obj.read()
    else:
        raise TypeError("Unsupported input type: {type(obj)} for to_bytes")

def to_text(obj: Union[bytes, BinaryIO, str], encoding="utf-8") -> str:
    if isinstance(obj, BytesIO):
        return obj.getvalue().decode(encoding)
    elif isinstance(obj, bytes):
        return obj.decode(encoding)
    elif isinstance(obj, str):
        return obj
    elif hasattr(obj, "read") and callable(obj.read):
        try:
            obj.seek(0)
        except Exception:
            pass
        return obj.read().decode(encoding)
    else:
        raise TypeError(f"Unsupported input type: {type(obj)} for to_text")

async def async_save_contents_to_path(contents: Union[BinaryIO, bytes, str], path: str, encoding="utf-8") -> None:
    loop = asyncio.get_event_loop()
    async with aiofiles.open(path, "wb") as f:
        if isinstance(contents, BytesIO):
            await f.write(contents.getvalue())
        elif isinstance(contents, str):
            # 文本模式转换为bytes写入
            await f.write(contents.encode(encoding))
        elif isinstance(contents, bytes):
            # 纯字节模式写入
            await f.write(contents)
        elif hasattr(contents, "read") and callable(contents.read):
            # 流式读取并写入
            try:
                contents.seek(0)
            except Exception:
                pass
            while True:
                chunk = await loop.run_in_executor(None, contents.read, 8192)
                if not chunk:
                    break
                await f.write(chunk)
        else:
            raise TypeError(f"Unsupported contents type: {type(contents)}. Must be str, bytes, or BinaryIO.")
    logger.info(f"Saved contents to {path} successfully.")
    return

def save_contents_to_path(contents: Union[BinaryIO, bytes, str], path: str, encoding="utf-8") -> None:
    with open(path, "wb") as f:
        if isinstance(contents, BytesIO):
            f.write(contents.getvalue())
        elif isinstance(contents, bytes):
            f.write(contents)
        elif isinstance(contents, str):
            f.write(contents.encode(encoding))
        elif hasattr(contents, "read") and callable(contents.read):
            # 重置指针到开头
            try:
                contents.seek(0)
            except Exception:
                pass  # 如果对象不支持 seek，比如 socket，可以跳过
            shutil.copyfileobj(contents, f, length=8192)  # 用同步的底层文件对象
        else:
            raise TypeError(f"Unsupported contents type: {type(contents)}. Must be str, bytes, or BinaryIO.")
    logger.info(f"Saved contents to {path} successfully.")
    return

def local_path_to_url(path: str, base_dir: str, base_url: str) -> str:
    if not path:
        return ""
    base_dir = Path(base_dir).resolve()
    full_path = Path(path).resolve()
    try:
        relative_path = full_path.relative_to(base_dir)
    except ValueError:
        raise ValueError(f"Local path {full_path} is not under base directory {base_dir}")
    # full_url = urljoin(base_url, str(rel_path))
    full_url = f"{base_url.rstrip('/')}/{relative_path.as_posix()}"
    return full_url

def url_to_local_path(url: str, base_dir: str, base_url: str) -> str:
    if not url:
        return ""
    if not url.startswith(base_url):
        raise ValueError(f"URL path {url}does not start with base_url: {base_url}")
    relative_path = url.rstrip('/')[len(base_url.rstrip('/')):].lstrip("/")
    relative_path = unquote(relative_path)
    base_dir = Path(base_dir).resolve()
    local_path = base_dir / relative_path
    full_path = str(local_path)
    return full_path

def convert_contents_to_base64(contents: Union[bytes, BinaryIO], extension) -> str:
    if isinstance(contents, BytesIO):
        contents = contents.getvalue()
    elif hasattr(contents, "read") and callable(contents.read):
        contents.seek(0)
        contents = contents.read()
    media_type = get_mime_from_extension(extension)
    data_url = f"data:{media_type};base64"
    base64_code = base64.b64encode(contents).decode('utf-8')
    base64_code = f'{data_url},{base64_code}'
    return base64_code

def get_short_data(data, return_data: bool, return_file: bool) -> Tuple[str, str]:
    # len('data:audio/wav;base64,'): 22
    short_data = f"{data[:30]}...{data[-20:]}"
    full_data = short_data if not return_data or return_file else data
    return full_data, short_data

def copy_file(src_path: str, dst_path: str) -> None:
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    try:
        shutil.copyfile(src_path, dst_path)
    except Exception as e:
        logger.error(f"文件复制失败: {e}")
        raise HTTPException(status_code=500, detail="文件复制失败")


