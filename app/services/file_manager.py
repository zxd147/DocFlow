import base64
import os
import re
import uuid
from io import BytesIO
from urllib.parse import urlparse, unquote

import httpx
from fastapi import HTTPException

from app.core.configs.settings import settings
from app.utils.file import get_extension_from_mime
from app.utils.logger import get_logger

logger = get_logger()

async def get_contents(request_data, mode, file):
    sno, uid, do_save, return_base64, return_type, extra, data = (
        request_data.sno,
        request_data.uid,
        request_data.do_save,
        request_data.return_base64,
        request_data.return_type,
        request_data.extra,
        request_data.data
    )
    file_contents = None
    split_name, split_ext = os.path.splitext(data.file_name or "")
    if data.is_empty() or not file:
        raise HTTPException(status_code=400, detail="Missing file information: no file_url, file_path, file_name, or uploaded file provided.")
    if file and mode == "upload":
        source_name = split_name or file.filename or uuid.uuid4().hex[:8]
        file_content_type = file.content_type or ""
        extension = get_extension_from_mime(file_content_type)
        source_format = next(iter([data.file_format, split_ext, extension, ".bin"]))
        # contents = await file.read()
        # size = len(contents)
        file_contents = file.file  # 直接使用 `UploadFile` 的文件对象
        file_contents.seek(0, 2)  # 移动到文件末尾
        source_size = file_contents.tell()  # 获取当前位置，即文件大小
        file_contents.seek(0)  # 将指针重置到文件开头
        file_info = f"Get File mode: file, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    elif data.file_url:
        parsed_url = urlparse(data.file_url)
        url_path = unquote(parsed_url.path)
        url_split_name, url_split_ext = os.path.splitext(os.path.basename(url_path))
        source_name = split_name or url_split_name or uuid.uuid4().hex[:8]
        async with httpx.AsyncClient() as client:
            response = await client.get(data.file_url, timeout=10.0)
            response.raise_for_status()
            file_contents = response.content  # 直接使用 `httpx.Response` 的内容对象
            source_size = len(file_contents)
        file_content_type = response.headers.get("content-type", "")
        extension = get_extension_from_mime(file_content_type)
        source_format = next(iter([data.file_format, split_ext, url_split_ext, extension, ".bin"]))
        file_info = f"Get File mode: url, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    elif data.file_base64:
        extension = ''
        source_base64 = ''
        source_name = split_name or uuid.uuid4().hex[:8]
        if data.file_base64.startswith("data:"):
            # 使用正则表达式提取文件格式
            match = re.match(r'data:(.*?);base64,(.*)', data.file_base64)
            if match:
                mime_content_type = match.group(1)
                extension = get_extension_from_mime(mime_content_type)
                source_base64 = match.group(2)
                # 从MIME类型中提取文件格式
        source_format = next(iter([data.file_format, split_ext, extension, ".bin"]))
        # 解码 base64 编码的文件
        file_bytes = base64.b64decode(source_base64 or data.file_base64)
        file_contents = BytesIO(file_bytes)
        source_size = len(file_bytes)
        file_info = f"Get File mode: base64, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    elif data.file_path:
        if not os.path.exists(data.file_path):
            raise HTTPException(status_code=404, detail="File not found")
        path_split_name, path_split_ext = os.path.splitext(os.path.basename(data.file_path))
        source_name = split_name or path_split_name or uuid.uuid4().hex[:8]
        source_format = next(iter([data.file_format, split_ext, path_split_ext, ".bin"]))
        with open(data.file_path, "rb") as f:
            file_contents = f.read()
            source_size = len(file_contents)
        file_info = f"Get file mode: path, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    elif data.file_name and mode == "download":
        source_name = split_name or uuid.uuid4().hex[:8]
        source_format = next(iter([data.file_format, split_ext, ""]))
        file_path = os.path.join(settings.protected_manager_dir, f"{source_name}{source_format}")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        with open(file_path, "rb") as f:
            file_contents = f.read()
            source_size = len(file_contents)
        file_info = f"Get File mode: name, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    else:
        raise HTTPException(status_code=400, detail="Unsupported file mode provided. Missing file information: no file_url, file_path, file_base64, file_name, or uploaded file provided.")
    return file_contents, source_name, source_format, source_size, file_info



