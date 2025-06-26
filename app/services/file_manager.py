import base64
import copy
import json
import os
import traceback
import uuid
from io import BytesIO
from pathlib import Path
from typing import Union
from urllib.parse import urlparse, unquote

from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.configs.settings import settings
from app.models.request_model import FileModelRequest
from app.models.response_model import FileModelResponse, FileDataResponse
from app.services.convert_file import convert_pdf_to_docx, convert_docx_to_html
from app.utils.exception import file_exception
from app.utils.file import get_bytes_from_url, async_get_bytes_from_path, get_bytes_from_file, get_bytes_from_base64, \
    convert_contents_to_base64, \
    to_bytesio, to_text, copy_file, get_full_path, get_short_data, async_save_contents_to_path, \
    local_path_to_url, add_timestamp_to_filepath
from app.utils.logger import get_logger

logger = get_logger()

conversion_map = {
    "pdf2docx": convert_pdf_to_docx,
    "docx2html": convert_docx_to_html,
    # 其他...
}

async def handle_file_operation(request_model, file, mode, convert_type=None) -> Union[JSONResponse, StreamingResponse]:
    try:
        logger.info(f"{mode.capitalize()} file request param: {request_model.model_dump()}.")
        contents, name, ext, size, info = await get_contents(request_model, mode=mode, file=file)
        logger.info(info)
        if not contents or not info:
            raise ValueError("No valid file content found.")
        if mode == "upload" or mode == "extract":
            return_url, return_path = await save_file_and_get_url(request_model.data.file_path, settings.protected_manager_dir, contents, request_model.do_save, name, ext)
            text_data = to_text(contents) if request_model.return_text else ''
        elif mode == "convert":
            _, save_path = await save_file_and_get_url(request_model.data.file_path, settings.public_manager_dir, contents, request_model.do_save, name, ext)
            stream = BytesIO()
            contents = to_bytesio(contents)
            convert_path, convert_text, convert_contents = await conversion_map[convert_type](input_stream=contents, output_stream=stream)
            text_data = to_text(convert_text) if request_model.return_text else ''
            url, path, name, ext = await get_convert_path_and_url(save_path, contents, convert_type)
            return_url, return_path, contents = url, path, convert_contents
        elif mode == "download":
            return_url = request_model.data.file_url
            return_path = request_model.data.file_payh
            if return_url and return_url.startswith(settings.protected_manager_url):
                return_url = return_url.replace(settings.protected_manager_url, settings.public_manager_url)
                copy_file(return_path, return_path)
            elif return_path and return_path.startswith(settings.public_manager_dir):
                return_path = return_path.replace(settings.protected_manager_dir, settings.public_manager_dir)
                copy_file(return_path, return_path)
            text_data = to_text(contents) if request_model.return_text else ''
        else:
            return_url = request_model.data.file_url
            return_path = request_model.data.file_path
            text_data = to_text(contents) if request_model.return_text else ''
        code = 0
        messages = f"File {mode}ed successfully. {info}"
        # from app.utils.file import to_bytes
        # contents = to_bytes(contents)
        base64_data = convert_contents_to_base64(contents, ext)
        full_base64, short_base64 = get_short_data(base64_data, request_model.return_base64, request_model.return_file)
        full_text, short_text = get_short_data(text_data, request_model.return_text, request_model.return_file)
        results, results_log = build_results(request_model, code, messages, name, ext, return_path, return_url,
                                             full_base64, short_base64, full_text, short_text)
        logger.info(f"{mode.capitalize()} file response param: {results_log.model_dump()}.")
        return build_response(contents, results, name, ext, request_model.return_file)
    except Exception as e:
        code, status, msg = file_exception(e)
        logger.error(traceback.format_exc())
        logger.error(msg)
        return JSONResponse(
            status_code=status,
            content=FileModelResponse(code=code, messages=msg).model_dump()
        )

async def parse_file_request(request) -> FileModelRequest:
    request_content_type = request.headers.get('content-type', '')
    if 'multipart/form-data' in request_content_type or 'application/x-www-form-urlencoded' in request_content_type:
        form_data = await request.form()
        request_data = FileModelRequest(**form_data)
    elif "application/json" in request_content_type:
        json_data = await request.json()
        request_data = FileModelRequest(**json_data)
    else:
        raise HTTPException(status_code=415, detail="Unsupported Content-Type")
    return request_data

async def get_contents(request_data, mode, file):
    data = request_data.data
    split_name, split_ext = os.path.splitext(data.file_name or "")
    if data.is_empty() and not file:
            raise HTTPException(status_code=400, detail=f"Missing file information, data.is_empty: {request_data.data.is_empty()} and not file: {not file}.")
    if file and mode != "download":
        file_split_name, file_split_ext = os.path.splitext(file.filename or "")
        source_name = split_name or file_split_name or file.filename or uuid.uuid4().hex[:8]
        source_contents, source_size, file_extension = get_bytes_from_file(file)
        source_format = data.file_format or split_ext or file_split_ext or file_extension or ".bin"
        source_info = f"Get File mode: file, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    elif data.file_url:
        parsed_url = urlparse(data.file_url)
        url_path = unquote(parsed_url.path)
        url_split_name, url_split_ext = os.path.splitext(os.path.basename(url_path))
        source_name = split_name or url_split_name or uuid.uuid4().hex[:8]
        source_contents, source_size, file_extension = await get_bytes_from_url(data.file_url)
        source_format = data.file_format or split_ext or url_split_ext or file_extension or ".bin"
        source_info = f"Get File mode: url, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    elif data.file_base64 and mode != "download":
        source_name = split_name or uuid.uuid4().hex[:8]
        source_contents, source_size, file_extension = get_bytes_from_base64(data.file_base64)
        source_format = data.file_format or split_ext or file_extension or ".bin"
        source_info = f"Get File mode: base64, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    elif data.file_path and mode != "upload":
        path_split_name, path_split_ext = os.path.splitext(os.path.basename(data.file_path))
        source_name = split_name or path_split_name or uuid.uuid4().hex[:8]
        source_format = data.file_format or split_ext or  path_split_ext or ".bin"
        source_contents, source_size = await async_get_bytes_from_path(data.file_path)
        source_info = f"Get file mode: path, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    elif data.file_name and mode != "upload":
        source_name = split_name or uuid.uuid4().hex[:8]
        source_format = data.file_format or split_ext or ""
        file_path = os.path.join(settings.temp_manager_dir, f"{source_name}{source_format}")
        source_contents, source_size = await async_get_bytes_from_path(file_path)
        source_info = f"Get File mode: name, Name: {source_name}, Format: {source_format}, Size: {source_size} bytes."
    else:
        raise HTTPException(status_code=400, detail="Unsupported file mode provided. Missing file information: no file_url, file_path, file_base64, file_name, or uploaded file provided.")
    return source_contents, source_name, source_format, source_size, source_info

async def save_file_and_get_url(file_path, directory, contents, do_save, name, ext):
    st_fmt = "full" if do_save else "null"
    save_path = get_full_path(directory, file_path, name, ext, st_fmt)
    save_url = local_path_to_url(save_path, settings.static_root, settings.static_url) \
        if save_path and save_path.startswith(settings.static_root) else ''
    await async_save_contents_to_path(contents, save_path) if do_save else None
    return save_url, save_path

async def get_convert_path_and_url(file_path, contents, convert_type):
    src_ext, dst_ext = convert_type.split("2", 1)
    if os.path.splitext(file_path)[1] != f".{src_ext}":
        raise ValueError(f"文件{file_path}扩展名与转换类型不匹配: {os.path.splitext(file_path)[1]} != .{src_ext}")
    # 用新的扩展名替换原来的
    convert_path = str(Path(file_path).with_suffix(f".{dst_ext}"))

    convert_path = add_timestamp_to_filepath(convert_path, fmt='minute')
    convert_name, convert_ext = os.path.splitext(os.path.basename(convert_path))
    convert_url = local_path_to_url(convert_path, settings.static_root, settings.static_url) \
        if convert_path and convert_path.startswith(settings.static_root) else ''
    await async_save_contents_to_path(contents, convert_path)
    return convert_url, convert_path, convert_name, convert_ext

# 提取的通用工具模块
def build_results(request, code, messages, name, ext, path, url, full_base64, short_base64, full_text, short_text):
    data = FileDataResponse(file_name=name, file_format=ext, file_url=url, file_path=path, file_base64=full_base64, file_text=full_text)
    results = FileModelResponse(uid=request.uid, sno=request.sno, code=code, messages=messages, data=data)
    results_log = copy.deepcopy(results)
    results_log.data.file_base64 = short_base64
    results_log.data.file_text = short_text
    return results, results_log

def build_response(file_contents, results, name, ext, return_file, media_type="application/octet-stream"):
    if file_contents and return_file:
        metadata_json = json.dumps(results.model_dump(), ensure_ascii=False)
        metadata_b64 = base64.b64encode(metadata_json.encode()).decode()
        filename = f"{name}{ext}"
        headers = {"X-File-Metadata": metadata_b64, "Content-Disposition": f'attachment; filename="{filename}"',}
        file_contents = to_bytesio(file_contents)
        return StreamingResponse(file_contents, media_type=media_type, headers=headers)
        # return StreamingResponse(file_contents, media_type=media_type)
    else:
        return JSONResponse(status_code=200, content=results.model_dump())



