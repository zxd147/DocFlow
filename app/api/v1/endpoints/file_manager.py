import base64
import copy
import json
from typing import Optional

from fastapi import APIRouter
from fastapi import File, UploadFile
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.configs.settings import settings
from app.models.request_model import FileExtractRequest, FileConvertRequest, FileRequestModel
from app.models.response_model import FileUploadResponse, FileDataResponse, FileResponseModel
from app.services.file_manager import get_contents
from app.utils.file import analyze_path, save_contents_to_path, local_path_to_url, \
    convert_contents_to_base64, parse_file_request
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger()

@router.post("/upload_file")
async def upload_file(request: Request, file: Optional[UploadFile] = File(None)):
    try:
        request = await parse_file_request(request)
        logger.info(f"Upload file request param: {request.model_dump()}.")
        if request.data.is_empty() or not file:
            raise HTTPException(status_code=400, detail="Missing file information: no file_url, file_path, or uploaded file provided.")
        file_contents, save_name, save_format, save_size, file_info = await get_contents(request, mode="upload", file=file)
        logger.info(file_info)
        if not file_contents or not file_info:
            raise ValueError("No valid file content found.")
        # 将文件内容编码为 base64
        # len('data:audio/wav;base64,'): 22
        save_base64 = convert_contents_to_base64(file_contents, save_format)
        save_base64_simple = f"{save_base64[:30]}...{save_base64[-20:]}"  # 只记录前30个字符
        save_base64 = save_base64_simple if not request.return_base64 or request.return_type == "file" else save_base64
        save_path = analyze_path(settings.protected_manager_dir, request.data.file_path, save_name, save_format)
        save_url = local_path_to_url(save_path, settings.static_root, settings.static_url) if save_path.startswith(settings.protected_manager_dir) else ''
        # save file to disk
        save_contents_to_path(file_contents, save_path) if request.do_save else None
        upload_logs = f"File uploaded and saved successfully."
        logger.info(upload_logs)
        messages = f"{upload_logs} {file_info}"
        results = FileUploadResponse(uid=request.uid, sno=request.sno, code=0, messages=messages,
                                     data=FileDataResponse(file_url=save_url, file_path=save_path, file_name=save_name,
                                                           file_base64=save_base64, file_format=save_format))
        results_log = copy.deepcopy(results)
        results_log.audio_base64 = save_base64_simple
        logger.info(f"Upload file response param: {results_log.model_dump()}.")
        if request.return_type == "file":
            metadata_json = json.dumps(results.model_dump(), ensure_ascii=False)
            metadata_b64 = base64.b64encode(metadata_json.encode()).decode()
            headers = {"X-File-Metadata": metadata_b64}
            # file_contents 是 bytes 或 file-like
            return StreamingResponse(file_contents, media_type="application/octet-stream", headers=headers)
        else:
            return JSONResponse(status_code=200, content=results.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/download_file")
async def download_file(request: FileRequestModel):
    try:
        logger.info(f"Download file request param: {request.model_dump()}.")
        if request.data.is_empty():
            raise HTTPException(status_code=400,
                                detail="Missing file information: no file_url, file_path, or file_name provided.")
        file_contents, load_name, load_format, load_size, file_info = await get_contents(request, mode="download", file=None)
        upload_logs = f"File download successfully."
        logger.info(file_info)
        messages = f"{upload_logs} {file_info}"
        if not file_contents or not file_info:
            raise ValueError("No valid file content found.")
        save_base64 = convert_contents_to_base64(file_contents, load_format)
        save_base64_simple = f"{save_base64[:30]}...{save_base64[-20:]}"  # 只记录前30个字符
        save_base64 = save_base64_simple if not request.return_base64 or request.return_type == "file" else save_base64
        results = FileResponseModel(uid=request.uid, sno=request.sno, code=0, messages=messages,
                                     data=FileDataResponse(file_url=request.data.file_url, file_path=request.data.file_path,
                                          file_name=request.data.file_name,file_base64=save_base64, file_format=load_format))
        results_log = copy.deepcopy(results)
        results_log.audio_base64 = save_base64_simple
        logger.info(f"Download file response param: {results.model_dump()}.")
        if request.return_type == "file":
            metadata_json = json.dumps(results.model_dump(), ensure_ascii=False)
            metadata_b64 = base64.b64encode(metadata_json.encode()).decode()
            headers = {"X-File-Metadata": metadata_b64}
            # file_contents 是 bytes 或 file-like
            return StreamingResponse(file_contents, media_type="application/octet-stream", headers=headers)
        else:
            return JSONResponse(status_code=200, content=results.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/extract_text")
def extract_text(request: FileExtractRequest):
    logger.info(f"Extract file request param: {request.model_dump()}.")
    if request.data.is_empty():
        raise HTTPException(status_code=400,
                            detail="Missing file information: no file_url, file_path, or file_name provided.")

    results = FileUploadResponse(
        uid=request.uid,
        sno=request.sno,
        code=0,
        messages="",
        data=FileDataResponse(
            file_url=request.data.file_url,
            file_path=request.data.file_path,
            file_name=request.data.file_name
        )
    )
    logger.info(f"Extract file response param: {results.model_dump()}.")
    return JSONResponse(status_code=200, content=results.model_dump())

@router.post("/convert_file")
def convert_file(request: FileConvertRequest):
    return ...

@router.post("/pdf2docx")
def pdf2docx(request: Request):
    return ...

@router.post("/docx2html")
def docx2html(request: Request):
    return ...



