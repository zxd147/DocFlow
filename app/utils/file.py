import base64
import mimetypes
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Union, BinaryIO

from fastapi import HTTPException

from app.models.request_model import FileRequestModel
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
# 反向映射：后缀 => MIME
extension_mime_map = {v: k for k, v in mime_extension_map.items()}

def analyze_path(default_dir, file_path, file_name, file_format):
    has_ext = bool(os.path.splitext(file_path)[1])
    # 检查路径是否为完整路径
    if os.path.isabs(file_path):
        # 检查是否有文件后缀
        if has_ext and os.path.exists(os.path.dirname(file_path)):
            # 这是一个完整路径且父目录存在
            final_path = file_path
        elif os.path.isdir(file_path):
            # 这是一个存在的完整目录
            final_path = os.path.join(file_path, file_name + file_format)
        else:
            # 路径不存在或者不合法
            logs = f"Invalid file_path provided, {file_path}"
            logger.error(logs)
            raise ValueError(logs)
    elif file_path.find('/') == -1:
        # 不存在路径分隔符
        if has_ext:
            # 这是一个带后缀的文件名
            final_path = os.path.join(default_dir, file_path)
        elif file_path == '':
            final_path = os.path.join(default_dir, file_name + file_format)
        else:
            # 没有后缀名的文件名
            final_path = os.path.join(default_dir, file_path + file_format)
    else:
        if '/' in file_path and os.path.isdir(
                os.path.dirname(file_path) if has_ext else file_path):
            # 不是绝对路径但包含路径分隔符且存在, 这是一个相对目录
            logs = f"Warning: {file_path}, 相对路径仅供测试, 请使用绝对路径"
            logger.warning(logs)
            if has_ext:
                final_path = os.path.abspath(file_path)
            else:
                # file_path = str(os.path.join(file_path, file_name + file_format))
                file_path = os.path.join(file_path, f"{file_name}{file_format}")
                final_path = os.path.abspath(file_path)
        else:
            # 路径不存在或者不合法
            logs = f"Invalid file_path provided, {file_path}"
            logger.error(logs)
            raise ValueError(logs)
    dir_name = os.path.dirname(final_path)
    base_name = os.path.basename(final_path)
    os.makedirs(dir_name, exist_ok=True)
    name, ext = os.path.splitext(base_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}[{timestamp}]{ext}"
    final_path = os.path.join(dir_name, filename)
    return final_path


def get_extension_from_mime(content_type: str) -> str:
    extension = mime_extension_map.get(content_type) or mimetypes.guess_extension(content_type, strict=False) or ""
    return extension

def get_mime_from_extension(extension: str) -> str:
    extension = "." + extension if not extension.startswith(".") else extension
    mime = extension_mime_map.get(extension.lower()) or mimetypes.guess_type("file" + extension, strict=False)[0] or ""
    return mime

def save_contents_to_path(contents: Union[bytes, BinaryIO], path: str) -> None:
    with open(path, "wb") as f:
        if isinstance(contents, bytes):
            f.write(contents)
        else:
            shutil.copyfileobj(contents, f)  # 用同步的底层文件对象

def local_path_to_url(file_path: str, base_dir: str, base_url: str) -> str:
    base_dir = Path(base_dir)
    full_path = Path(file_path).resolve()
    rel_path = full_path.relative_to(base_dir)
    # full_url = urljoin(base_url, str(rel_path))
    full_url = f"{base_url.rstrip('/')}/{rel_path.as_posix()}"
    return full_url

def convert_contents_to_base64(contents: Union[bytes, BinaryIO], format) -> str:
    media_type = get_mime_from_extension(format)
    data_url = f"data:{media_type};base64"
    base64_code = base64.b64encode(contents).decode('utf-8')
    base64_code = f'{data_url},{base64_code}'
    return base64_code

async def parse_file_request(request) -> FileRequestModel:
    request_content_type = request.headers.get('content-type', '')
    if 'multipart/form-data' in request_content_type or 'application/x-www-form-urlencoded' in request_content_type:
        form_data = await request.form()
        request_data = FileRequestModel(**form_data)
    elif "application/json" in request_content_type:
        json_data = await request.json()
        request_data = FileRequestModel(**json_data)
    else:
        raise HTTPException(status_code=415, detail="Unsupported Content-Type")
    return request_data



