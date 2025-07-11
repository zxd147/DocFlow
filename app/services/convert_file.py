import os
import subprocess
from io import BytesIO, StringIO
from pathlib import Path
from typing import Union

import commonmark
import html2markdown
import html2text
import mammoth
import markdown as md
import marko
import mistune
import pandas as pd
import pdfkit
from bs4 import BeautifulSoup
from html2docx import html2docx
from markdown_it import MarkdownIt
from markdownify import markdownify
from markitdown import MarkItDown
from pdf2docx import Converter
from tomd import Tomd
from weasyprint import HTML

from app.models.file_conversion import FileConvertParams
from app.utils.file import raw_to_stream, stream_to_raw, seek_stream, async_save_string_or_bytes_to_path, \
    async_get_bytes_from_path, text_to_binary, gen_resource_locations
from app.utils.filetypes import markitdown_input_ext
from app.utils.logger import get_logger
from app.utils.text import strip_markdown, format_html

logger = get_logger()

async def convert_pdf_to_docx(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    output_stream = BytesIO()
    logger.info(f"Converting pdf to docx...")
    cv = Converter(pdf_file=params.input_path, stream=params.input_raw)
    cv.convert(output_stream, start=0, end=None)
    cv.close()
    seek_stream(output_stream)
    output_raw = stream_to_raw(output_stream)
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_docx_to_md_or_html(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    input_path, input_raw, input_stream = params.input_path, params.input_raw, params.input_stream
    images_dir = os.path.join(gen_resource_locations("publib", "images", params.extra.category)[0], params.extra.name)
    input_stream = raw_to_stream(input_raw) if not input_stream else input_stream
    if input_path and os.path.exists(input_path):
        with open(input_path, "rb") as docx_file:
            input_stream = BytesIO(docx_file.read())
    logger.info(f"Converting docx to html or markdown: {params.convert_type}...")
    if "2md" in params.convert_type:
        result = mammoth.convert_to_markdown(input_stream)
    else:
        # result = mammoth.convert_to_html(input_stream, convert_image=mammoth.images.skip)
        result = mammoth.convert_to_html(input_stream)
    result_raw = result.value
    # 格式化处理
    output_raw = await format_html(result_raw, params.extra.policy, images_dir) if "2md" not in params.convert_type else result_raw
    output_stream = raw_to_stream(output_raw)
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_pdf_to_md_or_html(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    docx_ext = "docx"
    src_ext, dst_ext = params.convert_type.lower().split("-")[0].split("_")[0].split("2", 1)
    docx_path = str(Path(params.input_path).with_suffix(f".{docx_ext}"))
    output_path = params.output_path
    params.convert_type = f"{src_ext}2{docx_ext}"
    params.output_path = docx_path
    docx_raw, docx_stream, docx_save_path = await convert_pdf_to_docx(params)
    params.convert_type = f"{docx_ext}2{dst_ext}"
    params.input_raw = docx_raw
    params.input_stream = docx_stream
    params.input_path = docx_path
    params.output_path = output_path
    output_raw, output_stream, output_path = await convert_docx_to_md_or_html(params)
    return output_raw, output_stream, output_path

async def convert_html_to_docx(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    input_raw = params.input_raw
    logger.info("Converting html to docx...")
    soup = BeautifulSoup(input_raw, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
    output_stream = html2docx(input_raw, title)
    seek_stream(output_stream)
    output_raw = stream_to_raw(output_stream)
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_docx_to_pdf(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    input_path, input_raw, output_path = params.input_path, params.input_raw, params.output_path
    if not os.path.exists(input_path):
        await async_save_string_or_bytes_to_path(input_raw, input_path)
    logger.info("Converting docx to pdf...")
    if "v2" in params.convert_type:
        subprocess.run(["pandoc", input_path, "-o", output_path], check=True)
    else:
        subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", os.path.dirname(output_path), input_path], check=True)
    output_raw, _ = await async_get_bytes_from_path(output_path)
    output_stream = raw_to_stream(output_raw)
    return output_raw, output_stream, output_path

async def convert_html_to_pdf(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    input_raw = params.input_raw
    if "v2" in params.convert_type:
        logger.info("Converting HTML to PDF using WeasyPrint...")
        output_stream = BytesIO()
        HTML(string=input_raw).write_pdf(output_stream)
        seek_stream(output_stream)
        output_raw = stream_to_raw(output_stream)
    else:
        logger.info("Converting HTML to PDF using Wkhtmltopdf...")
        output_raw = pdfkit.from_string(input_raw, False)
        output_stream = raw_to_stream(output_raw)
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_excel_and_markdown_or_html(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    convert_type, input_raw, input_stream = params.convert_type, params.input_raw, params.input_stream
    input_stream = raw_to_stream(input_raw) if not input_stream else input_stream
    output_stream = StringIO() if params.extra.is_text else BytesIO()
    dfs_dict, dfs = {}, []
    if "html2" in convert_type:
        dfs = pd.read_html(input_stream, encoding="utf-8")
    elif "csv2" in convert_type:
        dfs = [pd.read_csv(input_stream, encoding="utf-8")]  # 转为列表以保持一致
    elif "xls2" in convert_type:
        dfs_dict = pd.read_excel(input_stream, sheet_name=None, engine="xlrd")
    elif "xlsx2" in convert_type:
        dfs_dict = pd.read_excel(input_stream, sheet_name=None, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported convert file type: {convert_type}")
    sheet_names = list(dfs_dict.keys()) if dfs_dict else [f"Table{i + 1}" for i in range(len(dfs))]
    dfs = list(dfs_dict.values()) if dfs_dict else dfs
    if "2html" in convert_type:
        html_blocks = [df.to_html(index=False, border=1) for df in dfs]
        parts = [f"<h2>{name}</h2><br>\n{html}" for name, html in zip(sheet_names, html_blocks)]
        result_raw = "<br><hr><br>".join(parts)
        images_dir = os.path.join(gen_resource_locations("publib", "images", params.extra.category)[0], params.extra.name)
        output_raw = await format_html(result_raw, params.extra.policy, images_dir)
    elif "2md" in convert_type:
        md_blocks = [df.to_markdown(index=False) for df in dfs]
        parts = [f"## {name}\n\n{markdown}" for name, markdown in zip(sheet_names, md_blocks)]
        output_raw = "\n\n---\n\n".join(parts)
    elif "2csv" in convert_type:
        if len(dfs) > 1:
            for i, df in enumerate(dfs):
                df['TableName'] = sheet_names[i]
        df = pd.concat(dfs, ignore_index=True)
        output_raw = df.to_csv(index=False)
    else:
        with pd.ExcelWriter(output_stream, engine="openpyxl") as writer:
            for df, name in zip(dfs, sheet_names):
                df.to_excel(writer, sheet_name=name, index=False)
        seek_stream(output_stream)
        output_raw = stream_to_raw(output_stream)
    output_stream = raw_to_stream(output_raw) if output_stream.getvalue() == "" else output_stream
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_to_markdown(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    convert_type = params.convert_type
    if "2md" not in convert_type:
        raise ValueError("Only *2md conversions are supported with MarkItDown.")
    extension = convert_type.replace("2md", "").lower()
    # 安全性和鲁棒性检查
    if extension not in markitdown_input_ext:
        raise ValueError(f"Unsupported convert_type: {convert_type}")
    input_stream = raw_to_stream(text_to_binary(params.input_raw))
    result = MarkItDown().convert(input_stream)  # str, path (str or Path), url, requests.Response, BinaryIO
    output_raw = result.text_content
    output_stream = raw_to_stream(output_raw)
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_html_to_md(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    if "v5" in params.convert_type:
        input_stream = raw_to_stream(text_to_binary(params.input_raw))
        result = MarkItDown().convert(input_stream)  # str, path (str or Path), url, requests.Response, BinaryIO
        output_raw = result.text_content
    elif "v4" in params.convert_type:
        output_raw = html2markdown.convert(params.input_raw)
    elif "v3" in params.convert_type:
        output_raw = Tomd(params.input_raw).markdown
        # output_raw = Tomd().convert(params.input_raw)
    elif "v2" in params.convert_type:
        output_raw = html2text.html2text(params.input_raw)
    else:
        output_raw = markdownify(params.input_raw)
    output_stream = raw_to_stream(output_raw)
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_md_to_html(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    if "v5" in params.convert_type:
        parser = commonmark.Parser()
        renderer = commonmark.HtmlRenderer()
        ast = parser.parse(params.input_raw)
        output_raw = renderer.render(ast)
    elif "v4" in params.convert_type:
        output_raw = marko.convert(params.input_raw)
    elif "v3" in params.convert_type:
        output_raw = mistune.markdown(params.input_raw)
    elif "v2" in params.convert_type:
        output_raw = md.markdown(params.input_raw)
    else:
        output_raw = MarkdownIt().render(params.input_raw)
    images_dir = os.path.join(gen_resource_locations("publib", "images", params.extra.category)[0], params.extra.name)
    output_raw = await format_html(output_raw, params.extra.policy, images_dir)
    output_stream = raw_to_stream(output_raw)
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_html_to_html(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    images_dir = os.path.join(gen_resource_locations("publib", "images", params.extra.category)[0], params.extra.name)
    output_raw = await format_html(params.input_raw, params.extra.policy, images_dir)
    output_stream = raw_to_stream(output_raw)
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_md_to_txt(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    # markdown转为纯文本，使用正则表达式清除 Markdown 标记
    output_raw = await strip_markdown(params.input_raw)
    output_stream = raw_to_stream(output_raw)
    output_path = ""
    return output_raw, output_stream, output_path

async def convert_html_to_txt(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO], str]:
    # html转纯文本, 	用 BeautifulSoup 的 get_text() 方法,彻底清除无标记
    soup = BeautifulSoup(params.input_raw, "html.parser")
    output_raw = soup.get_text(separator="\n")  # type: ignore
    output_stream = raw_to_stream(output_raw)
    output_path = ""
    return output_raw, output_stream, output_path



