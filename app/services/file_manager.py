import base64
import copy
import json
import os
import traceback
import unicodedata
import uuid
from pathlib import Path
from typing import Union
from urllib.parse import urlparse, unquote, quote

from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.configs.settings import settings
from app.models.file_conversion import FileConvertParams
from app.models.file_conversion import FileDataModel
from app.models.request_model import FileModelRequest
from app.models.response_model import FileModelResponse
from app.utils.exception import file_exception
from app.utils.file import (async_get_bytes_from_file, get_bytes_from_url, async_get_bytes_from_path,
                            get_bytes_from_base64, get_full_path, add_timestamp_to_filepath, local_path_to_url,
                            url_to_local_path, convert_bytes_to_base64, async_save_string_or_bytes_to_path,
                            get_short_data, copy_file, binary_to_text, is_text_file, text_to_binary,
                            get_mime_from_extension, raw_to_stream, gen_resource_locations)
from app.utils.func_map import get_file_conversion
from app.utils.logger import get_logger

logger = get_logger()

def get_converter(convert_type):
    if "aspose" in convert_type:
        pass
    conversion_map = get_file_conversion()
    base_convert_type = convert_type.lower().split("_", 1)[0]
    converter = conversion_map.get(base_convert_type)
    if converter is None:
        raise ValueError(f"不支持的转换类型: {base_convert_type}")
    return converter

async def handle_file_operation(request_model: FileModelRequest, file, mode, convert_type='') -> Union[JSONResponse, StreamingResponse]:
    try:
        logger.info(f"{mode.capitalize()} file request param: {request_model.model_dump()}.")
        raw, name, extension, size, info = await get_raw(request_model, mode=mode, file=file)
        logger.info(info)
        extra, code = request_model.extra, 0
        category = extra.get("category", "manager")
        protected_dir, protected_url = gen_resource_locations("protected", "files", category)
        public_dir, public_url = gen_resource_locations("public", "files", category)
        if not raw:
            raise ValueError("No valid file raw found.")
        if mode == "upload":
            return_url, return_path = await save_file_and_get_url(request_model.data.file_path, protected_dir, raw, request_model.do_save, name, extension)
            return_raw, return_stream = (raw, raw_to_stream(raw)) if request_model.return_stream else (raw, None)
        elif mode == "convert":
            _, save_path = await save_file_and_get_url(request_model.data.file_path, public_dir, raw, request_model.do_save, name, extension)
            url, path, name, extension = await get_convert_path_and_url(save_path, convert_type)
            extra.setdefault("is_text", is_text_file(path))
            params_dict = {"convert_type": convert_type, "input_raw": raw, "input_path": save_path, "output_path": path, "extra": extra}
            params = FileConvertParams.from_dict(params_dict)
            converter = get_converter(convert_type)
            convert_raw, convert_stream = await converter(params)
            return_path = await async_save_string_or_bytes_to_path(convert_raw, path)
            return_url, return_raw, return_stream = url, convert_raw, convert_stream
        elif mode == "download":
            save_url = request_model.data.file_url
            save_path = request_model.data.file_path
            if not any([save_url, save_path]):
                raise ValueError("No valid file url or file path found.")
            elif save_url and save_url.startswith(protected_url):
                save_path = url_to_local_path(save_url, protected_url, protected_dir)
            if save_path.startswith(protected_dir):
                return_path = save_path.replace(protected_dir, public_dir)
                copy_file(save_path, return_path)
                return_url = local_path_to_url(return_path, public_url, public_dir)
            else:
                return_path = save_path
                return_url = save_url
            return_raw, return_stream = (raw, raw_to_stream(raw)) if request_model.return_stream else (raw, None)
        elif mode == "extract":
            return_url, return_path = "", ""
            return_raw, return_stream = (raw, raw_to_stream(raw)) if request_model.return_stream else (raw, None)
        elif mode == "fill":
            return_url, return_path = "", ""
            return_raw, return_stream = (raw, raw_to_stream(raw)) if request_model.return_stream else (raw, None)
        else:
            return_url = request_model.data.file_url
            return_path = request_model.data.file_path
            return_raw, return_stream = (raw, raw_to_stream(raw)) if request_model.return_stream else (raw, None)
        messages = f"File {mode}ed successfully. {info}"
        name = f"{name}{extension}"
        base64_str = convert_bytes_to_base64(raw, extension)
        full_base64, short_base64 = get_short_data(base64_str, request_model.return_base64, request_model.return_stream)
        full_raw, short_raw = get_short_data(return_raw, request_model.return_raw, request_model.return_stream)
        results, results_log = build_results(request_model, code, messages, extra, name, extension, return_url, return_path,
                                             full_base64, short_base64, full_raw, short_raw)
        logger.info(f"{mode.capitalize()} file response param: {results_log.model_dump()}.")
        if results.data.is_empty() and not return_stream:
            raise HTTPException(status_code=400, detail=f"No return file information, data.is_empty: {results.data.is_empty()} and not return_stream: {not return_stream}.")
        response = build_response(return_stream, results, name, extension, request_model.return_stream)
        return response
    except Exception as e:
        code, status, msg = file_exception(e)
        logger.error(traceback.format_exc())
        logger.error(msg)
        content = FileModelResponse(code=code, messages=msg).model_dump()
        return JSONResponse(status_code=status, content=content)

async def parse_file_request(request) -> FileModelRequest:
    request_content_type = request.headers.get('content-type', '')
    if 'multipart/form-data' in request_content_type or 'application/x-www-form-urlencoded' in request_content_type:
        form_data = await request.form()
        form_dict = dict(form_data)
        for key in ("extra","data", ):  # 可以扩展多个需要反序列化的字段
            value = form_dict.get(key)
            if key in form_dict and isinstance(value, str) and value.strip().startswith("{") and value.strip().endswith("}"):
                try:
                    form_dict[key] = json.loads(value)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON in 【'{key}': '{value}'】 field")
        request_data = FileModelRequest(**form_dict)
    elif "application/json" in request_content_type:
        json_data = await request.json()
        request_data = FileModelRequest(**json_data)
    else:
        raise HTTPException(status_code=415, detail="Unsupported Content-Type")
    return request_data

async def get_raw(request_data, mode, file) -> tuple[Union[str, bytes], str, str, int, str]:
    data = request_data.data
    category = request_data.extra.get("category", "manager")
    static_root: str = settings.static_root
    temp_dir = os.path.join(static_root, 'temp', 'files', category)
    split_name, split_ext = os.path.splitext(data.file_name or "")
    if data.is_empty() and not file:
            raise HTTPException(status_code=400, detail=f"Missing file information, data.is_empty: {request_data.data.is_empty()} and not file: {not file}.")
    if file and mode != "download":
        file_split_name, file_split_ext = os.path.splitext(file.filename or "")
        source_name = split_name or file_split_name or file.filename or uuid.uuid4().hex[:8]
        source_raw, _, file_extension = await async_get_bytes_from_file(file)
        source_ext = data.file_format or split_ext or file_split_ext or file_extension or ".bin"
        source_raw = binary_to_text(source_raw) if is_text_file(source_ext) else source_raw
        source_size = len(source_raw)
        source_info = f"Get File mode: file, Name: {source_name}, Extension: {source_ext}, Size: {source_size} bytes."
    elif data.file_url:
        parsed_url = urlparse(data.file_url)
        url_path = unquote(parsed_url.path)
        url_split_name, url_split_ext = os.path.splitext(os.path.basename(url_path))
        source_name = split_name or url_split_name or uuid.uuid4().hex[:8]
        source_raw, _, file_extension = await get_bytes_from_url(data.file_url)
        source_ext = data.file_format or split_ext or url_split_ext or file_extension or ".html"
        source_raw = binary_to_text(source_raw) if is_text_file(source_ext) else source_raw
        source_size = len(source_raw)
        source_info = f"Get File mode: url, Name: {source_name}, Extension: {source_ext}, Size: {source_size} bytes."
    elif data.file_base64 and mode != "download":
        source_name = split_name or uuid.uuid4().hex[:8]
        source_raw, _, file_extension = get_bytes_from_base64(data.file_base64)
        source_ext = data.file_format or split_ext or file_extension or ".bin"
        source_raw = binary_to_text(source_raw) if is_text_file(source_ext) else source_raw
        source_size = len(source_raw)
        source_info = f"Get File mode: base64, Name: {source_name}, Extension: {source_ext}, Size: {source_size} bytes."
    elif data.file_raw and mode != "download":
        source_name = split_name or uuid.uuid4().hex[:8]
        source_ext = data.file_format or split_ext or ".txt"
        source_raw = data.file_raw if is_text_file(source_ext) else text_to_binary(data.file_raw)
        source_size = len(source_raw)
        source_info = f"Get File mode: base64, Name: {source_name}, Extension: {source_ext}, Size: {source_size} bytes."
    elif data.file_path and mode != "upload":
        path_split_name, path_split_ext = os.path.splitext(os.path.basename(data.file_path))
        source_name = split_name or path_split_name or uuid.uuid4().hex[:8]
        source_ext = data.file_format or split_ext or  path_split_ext or ".bin"
        file_path = get_full_path(temp_dir, data.file_path, source_name, source_ext)
        source_raw, _ = await async_get_bytes_from_path(file_path)
        source_raw = binary_to_text(source_raw) if is_text_file(source_ext) else source_raw
        source_size = len(source_raw)
        source_info = f"Get file mode: path, Name: {source_name}, Extension: {source_ext}, Size: {source_size} bytes."
    elif data.file_name and mode != "upload":
        source_name = split_name or uuid.uuid4().hex[:8]
        source_ext = data.file_format or split_ext or ""
        file_path = os.path.join(temp_dir, f"{source_name}{source_ext}")
        source_raw, _ = await async_get_bytes_from_path(file_path)
        source_raw = binary_to_text(source_raw) if is_text_file(source_ext) else source_raw
        source_size = len(source_raw)
        source_info = f"Get File mode: name, Name: {source_name}, Extension: {source_ext}, Size: {source_size} {type(source_raw).__name__}."
    else:
        raise HTTPException(status_code=400, detail="Unsupported file mode provided. Missing file information: no file_url, file_path, file_base64, file_name, or uploaded file provided.")
    return source_raw, source_name, source_ext, source_size, source_info

async def save_file_and_get_url(path, directory, raw, do_save, name, extension):
    st_fmt = "full" if do_save else "null"
    save_path = get_full_path(directory, path, name, extension, st_fmt)
    save_url = local_path_to_url(save_path, settings.static_url, settings.static_root) \
        if save_path and save_path.startswith(settings.static_root) else ''
    save_path = await async_save_string_or_bytes_to_path(raw, save_path) if do_save else save_path
    return save_url, save_path

async def get_convert_path_and_url(path, convert_type):
    src_ext, dst_ext = convert_type.lower().split("_", 1)[0].split("2", 1)
    path_ext = os.path.splitext(path)[1]
    if path_ext != f".{src_ext}":
        raise ValueError(f"文件{path}扩展名与转换类型不匹配: {path_ext} != .{src_ext}")
    ext_path = Path(path).with_suffix(f".{dst_ext}")
    ts_path = Path(add_timestamp_to_filepath(str(ext_path), fmt='minute'))
    convert_name, convert_ext, convert_path = ts_path.stem, ts_path.suffix, str(ts_path)
    convert_url = local_path_to_url(convert_path, settings.static_url, settings.static_root) \
        if convert_path.startswith(settings.static_root) else ''
    return convert_url, convert_path, convert_name, convert_ext

# 提取的通用工具模块
def build_results(request, code, messages, extra, name, fmt, url, path, full_base64, short_base64, full_raw, short_raw):
    data = FileDataModel(file_name=name, file_format=fmt, file_base64=full_base64, file_raw=full_raw, file_url=url, file_path=path)
    results = FileModelResponse(uid=request.uid, sno=request.sno, code=code, messages=messages, extra=extra, data=data)
    results_log = copy.deepcopy(results)
    results_log.data.file_base64 = short_base64
    results_log.data.file_raw = short_raw
    return results, results_log

def build_response(content, results, name, extension, return_stream):
    if return_stream:
        metadata_json = json.dumps(results.model_dump(), ensure_ascii=False)
        # import base64
        metadata_b64 = base64.b64encode(metadata_json.encode()).decode()
        metadata_url = quote(metadata_json)
        quoted_name = quote(name)
        ascii_safe_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
        media_type = "application/octet-stream" or get_mime_from_extension(extension)
        headers = {"X-File-Metadata": metadata_url, "Content-Disposition": f'attachment; filename="{ascii_safe_name}"; filename*=UTF-8''{quoted_name}'}
        return StreamingResponse(content=content, media_type=media_type, headers=headers)
    else:

        return JSONResponse(status_code=200, content=results.model_dump())



