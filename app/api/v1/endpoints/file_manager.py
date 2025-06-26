from typing import Optional, Literal

from fastapi import APIRouter, Request, File, UploadFile

from app.models.request_model import FileModelRequest
from app.services.file_manager import parse_file_request, handle_file_operation
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger()

@router.post("/upload_file")
async def upload_file(request: Request, file: Optional[UploadFile] = File(None)):
    request = await parse_file_request(request)
    response = await handle_file_operation(request, file=file, mode="upload")
    return response

@router.post("/download_file")
async def download_file(request: FileModelRequest):
    response = await handle_file_operation(request, file=None, mode="download")
    return response

@router.post("/extract_text")
async def extract_text(request: FileModelRequest, file: Optional[UploadFile] = File(None)):
    request = await parse_file_request(request)
    response = await handle_file_operation(request, file=file, mode="extract")
    return response

@router.post("/convert_file/{convert_type}")
async def docx2html(request: Request, convert_type: Literal["pdf2docx", "pdf2html",
                    "docx2pdf", "docx2html", "html2docx", "html2pdf"] = "pdf2docx",
                    file: Optional[UploadFile] = File(None)):
    request = await parse_file_request(request)
    response = await handle_file_operation(request, file=file, mode="convert", convert_type=convert_type)
    return response



