import base64
import mimetypes
import os
import re
import shutil
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from typing import Union, BinaryIO, Tuple, TextIO
from urllib.parse import unquote

import aiofiles
import chardet
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
# 反向映射：后缀 => MIME
extension_mime_map = {v: k for k, v in mime_extension_map.items()}
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
binary_extensions = {
    ".xlsx", ".xls", ".xlsm",
    ".docx", ".doc", ".pptx", ".ppt",
    ".pdf", ".epub",
    ".zip", ".rar", ".7z",
    ".png", ".jpg", ".jpeg", ".bmp", ".gif",
    ".mp3", ".mp4", ".mov", ".avi",
    ".exe", ".dll", ".bin",
}
text_extensions = {
        ".csv", ".tsv", ".txt", ".log", ".md", ".rst", ".ini", ".cfg",
        ".json", ".xml", ".yaml", ".yml",
        ".html", ".htm", ".xhtml",
        ".tex", ".rtf", ".srt",
        ".py", ".js", ".css", ".java", ".cpp", ".c", ".sh", ".bat"
    }

def get_full_path(default_dir, path, name, extension, st_fmt="null") -> str:
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

async def async_get_bytes_from_file(file: UploadFile, _=False) -> Tuple[bytes, int, str]:
    raw = await file.read()
    size = len(raw)
    extension = get_extension_from_mime(file.content_type or "")
    return raw, size, extension

def get_bytes_from_file(file: UploadFile, _=False) -> Tuple[bytes, int, str]:
    raw = file.file.read()  # 直接使用 `UploadFile` 的文件对象
    size = len(raw)
    extension = get_extension_from_mime(file.content_type or "")
    return raw, size, extension

def get_file_like_from_file(file: UploadFile, _=False) -> Tuple[BinaryIO, int, str]:
    stream = file.file  # 直接使用 `UploadFile` 的文件对象
    stream.seek(0, 2)  # 移动到文件末尾
    size = stream.tell()  # 获取当前位置，即文件大小
    stream.seek(0)  # 将指针重置到文件开头
    extension = get_extension_from_mime(file.content_type or "")
    return stream, size, extension

async def async_get_bytes_from_path(path: str) -> Tuple[Union[str, bytes], int]:
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    async with aiofiles.open(path, "rb") as f:
        raw = await f.read()
    size = len(raw)
    return raw, size

def get_bytes_from_path(path: str) -> Tuple[Union[str, bytes], int]:
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(path, "rb") as f:
        raw = f.read()
    size = len(raw)
    return raw, size

async def get_bytes_from_url(url: str) -> Tuple[bytes, int, str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        raw = response.content  # 直接使用 `httpx.Response` 的内容对象
        content_type = response.headers.get("content-type", "")
    size = len(raw)
    extension = get_extension_from_mime(content_type)
    return raw, size, extension

def get_bytes_from_base64(base64_str: str) -> Tuple[bytes, int, str]:
    extension = ''
    if base64_str.startswith("data:"):
        # 使用正则表达式提取文件格式
        match = re.match(r'data:(.*?);base64,(.*)', base64_str)
        if match:
            content_type = match.group(1)
            extension = get_extension_from_mime(content_type)
            base64_str = match.group(2)
    raw = base64.b64decode(base64_str)
    size = len(raw)
    return raw, size, extension

def is_text_file(path: str) -> bool:
    return any(path.lower().endswith(extension) for extension in text_extensions)

def is_stream(obj: Union[TextIO, BinaryIO]) -> bool:
    return hasattr(obj, "read") and callable(getattr(obj, "read", None))

def seek_stream(obj: Union[TextIO, BinaryIO], seek_to: int=0) -> None:
    try:
        obj.seek(seek_to)
    except AttributeError:
        pass

def read_stream(obj: Union[TextIO, BinaryIO]) -> Union[str, bytes]:
    seek_stream(obj)
    raw = obj.read()
    seek_stream(obj)
    return raw

def encode_string(string: str, encoding="utf-8") -> bytes:
    default_encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
    encodings = [encoding]
    encodings.extend(default_encodings)
    for enc in encodings:
        try:
            return string.encode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Failed to decode data with available encodings.")

def decode_bytes(byte: bytes, encoding="utf-8") -> str:
    default_encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
    chardet_encoding = chardet.detect(byte)['encoding'] or encoding
    encodings = [encoding] if chardet_encoding == encoding else [chardet_encoding, encoding]
    encodings.extend(default_encodings)
    for enc in encodings:
        try:
            return byte.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Failed to decode data with available encodings.")

def encode_stringio(stringio: StringIO, encoding="utf-8") -> BytesIO:
    return wrap_bytes(encode_string(unwrap_stringio(stringio), encoding))

def decode_bytesio(bytesio: BytesIO, encoding="utf-8") -> StringIO:
    return wrap_string(decode_bytes(unwrap_bytesio(bytesio), encoding))

def encode_stream(stream: Union[TextIO, BinaryIO], encoding="utf-8") -> BytesIO:
    return wrap_bytes(text_to_binary(unwrap_stream(stream), encoding))

def decode_stream(stream: Union[TextIO, BinaryIO], encoding="utf-8") -> StringIO:
    return wrap_string(binary_to_text(unwrap_stream(stream), encoding))

def wrap_string(string: str) -> StringIO:
    return StringIO(string)

def wrap_bytes(byte: bytes) -> BytesIO:
    return BytesIO(byte)

def unwrap_stringio(stringio: StringIO) -> str:
    return stringio.getvalue()

def unwrap_bytesio(bytesio: BytesIO) -> bytes:
    return bytesio.getvalue()

def unwrap_stream(stream: Union[TextIO, BinaryIO]) -> Union[str, bytes]:
    return read_stream(stream)

def raw_to_stream(raw: Union[str, bytes, TextIO, BinaryIO]) -> Union[StringIO, BytesIO]:
    if isinstance(raw, (StringIO, BytesIO)):
        seek_stream(raw)
        return raw
    elif isinstance(raw, str):
        return wrap_string(raw)
    elif isinstance(raw, bytes):
        return wrap_bytes(raw)
    elif is_stream(raw):
        return raw_to_stream(unwrap_stream(raw))
    else:
        raise TypeError(f"Unsupported input type: {type(raw)}")

def stream_to_raw(stream: Union[str, bytes, TextIO, BinaryIO]) -> Union[str, bytes]:
    if isinstance(stream, (str, bytes)):
        return stream
    elif isinstance(stream, StringIO):
        return unwrap_stringio(stream)
    elif isinstance(stream, BytesIO):
        return unwrap_bytesio(stream)
    elif is_stream(stream):
        return stream_to_raw(unwrap_stream(stream))
    else:
        raise TypeError(f"Unsupported stream type: {type(stream)}")

def text_to_binary(text: Union[str, bytes, TextIO, BinaryIO], encoding="utf-8") -> Union[bytes, BytesIO]:
    if isinstance(text, (bytes, BytesIO)):
        seek_stream(text)
        return text
    elif isinstance(text, str):
        return encode_string(text, encoding)    # 如果是 str
    elif isinstance(text, StringIO):
        return encode_stringio(text, encoding)
    # 如果是文件类对象
    elif is_stream(text):
        return encode_stream(text, encoding)
    else:
        raise TypeError(f"Unsupported data type for encoding: {type(text)}")

def binary_to_text(binary: Union[str, bytes, TextIO, BinaryIO], encoding="utf-8") -> Union[str, StringIO]:
    if isinstance(binary, (str, StringIO)):
        seek_stream(binary)
        return binary
    elif isinstance(binary, bytes):
        return decode_bytes(binary, encoding)
    elif isinstance(binary, BytesIO):
        return decode_bytesio(binary, encoding)
    elif is_stream(binary):
        return decode_stream(binary, encoding)
    else:
        raise TypeError(f"Unsupported data type for decoding: {type(binary)}")

def ensure_string(obj: Union[str, bytes, TextIO, BinaryIO], encoding="utf-8") -> str:
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, bytes):
        return obj.decode(encoding)
    elif isinstance(obj, StringIO):
        return obj.getvalue()
    elif isinstance(obj, BytesIO):
        return obj.getvalue().decode(encoding)
    elif is_stream(obj):
        return ensure_string(read_stream(obj))
    else:
        raise TypeError(f"Unsupported input type: {type(obj)} for to_string")

def ensure_bytes(obj: Union[str, bytes, TextIO, BinaryIO], encoding="utf-8") -> bytes:
    if isinstance(obj, str):
        return obj.encode(encoding)
    elif isinstance(obj, bytes):
        return obj
    elif isinstance(obj, StringIO):
        return obj.getvalue().encode(encoding)
    elif isinstance(obj, BytesIO):
        return obj.getvalue()
    elif is_stream(obj):
        return ensure_bytes(read_stream(obj))
    else:
        raise TypeError("Unsupported input type: {type(obj)} for to_bytes")

def ensure_stringio(obj: Union[str, bytes, TextIO, BinaryIO], encoding="utf-8") -> StringIO:
    if isinstance(obj, str):
        return StringIO(obj)
    elif isinstance(obj, bytes):
        return StringIO(obj.decode(encoding))
    elif isinstance(obj, StringIO):
        seek_stream(obj)
        return obj
    elif isinstance(obj, BytesIO):
        return StringIO(obj.getvalue().decode(encoding))
    elif is_stream(obj):
        return ensure_stringio(read_stream(obj))
    else:
        raise TypeError(f"Unsupported type: {type(obj)} for to_stringio")

def ensure_bytesio(obj: Union[str, bytes, TextIO, BinaryIO], encoding="utf-8") -> BytesIO:
    if isinstance(obj, str):
        return BytesIO(obj.encode(encoding))
    elif isinstance(obj, bytes):
        return BytesIO(obj)
    elif isinstance(obj, StringIO):
        return BytesIO(obj.getvalue().encode(encoding))
    elif isinstance(obj, BytesIO):
        seek_stream(obj)
        return obj
    elif is_stream(obj):
        return ensure_bytesio(read_stream(obj))
    else:
        raise TypeError(f"Unsupported type: {type(obj)} for to_bytesio")

async def async_save_string_or_bytes_to_path(raw: Union[bytes, str], path: str, encoding="utf-8") -> str:
    # os.makedirs(os.path.dirname(path), exist_ok=True)  # 不自动创建目录，避免因传参错误而意外生成无效目录结构
    encoding = chardet.detect(raw)['encoding'] or encoding if isinstance(raw, bytes) else encoding
    if not isinstance(raw, (str, bytes)):
        raise TypeError(f"Unsupported raw type: {type(raw)}. Must be str or bytes.")
    if is_text_file(path):
        async with aiofiles.open(path, "w", encoding=encoding) as f:
            await f.write(binary_to_text(raw, encoding))
    else:
        async with aiofiles.open(path, "wb") as f:
            await f.write(text_to_binary(raw, encoding))
    logger.info(f"Saved raw to file {path} successfully.")
    return path

def save_string_or_bytes_to_path(raw: Union[bytes, str], path: str, encoding="utf-8") -> str:
    # os.makedirs(os.path.dirname(path), exist_ok=True)  # 不自动创建目录，避免因传参错误而意外生成无效目录结构
    is_text = is_text_file(path)
    mode = "w" if is_text else "wb"
    encoding = chardet.detect(raw)['encoding'] or encoding if isinstance(raw, bytes) else encoding
    with open(path, mode, encoding=encoding) as f:
        if isinstance(raw, str):
            f.write(raw if is_text else text_to_binary(raw, encoding))
        elif isinstance(raw, bytes):
            f.write(binary_to_text(raw, encoding) if is_text else raw)
        else:
            raise TypeError(f"Unsupported raw type: {type(raw)}. Must be str or bytes.")
    logger.info(f"Saved raw to {path} successfully.")
    return path

def convert_bytes_to_base64(raw: Union[str, bytes], extension, encoding="utf-8") -> str:
    if isinstance(raw, str):
        raw = raw.encode(encoding)
    media_type = get_mime_from_extension(extension)
    base64_head = f"data:{media_type};base64"
    base64_data = base64.b64encode(raw).decode("utf-8")
    base64_str = f'{base64_head},{base64_data}'
    return base64_str

def local_path_to_url(path: str, base_url: str, base_dir: str) -> str:
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

def url_to_local_path(url: str, base_url: str, base_dir: str) -> str:
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

def get_short_data(data, return_data: bool, return_stream: bool) -> Tuple[str, str]:
    # len('data:audio/wav;base64,'): 22
    short_data = f"{data[:50]}...{data[-20:]}"
    full_data = short_data if not return_data or return_stream else data
    return full_data, short_data

def copy_file(src_path: str, dst_path: str) -> None:
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    try:
        shutil.copyfile(src_path, dst_path)
    except Exception as e:
        logger.error(f"文件复制失败: {e}")
        raise HTTPException(status_code=500, detail="文件复制失败")


