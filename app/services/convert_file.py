import os
from io import BytesIO, StringIO
from typing import Union

import html2markdown
import html2text
import mammoth
import markdown as md
import mistune
import pandas as pd
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from markdown_it import MarkdownIt
from markitdown import MarkItDown
from pdf2docx import Converter
from tomd import Tomd

from app.models.file_conversion import FileConvertParams
from app.utils.file import raw_to_stream, stream_to_raw, seek_stream
from app.utils.logger import get_logger

logger = get_logger()

def remove_html_nested_tables(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    # 找出所有 table
    all_tables = soup.find_all("table")
    for table in all_tables:
        # 如果 table 有父级是 table，则为嵌套
        if table.find_parent("table"):
            # 用 table 的 children 直接替换整个 table 标签
            # table.unwrap()  # unwrap 会移除标签但保留内容
            text = table.get_text(strip=True)  # separator=" ",
            # text = text.replace("\n", " ").replace("  ", " ")
            table.replace_with(NavigableString(text))
    final_html = str(soup)
    return final_html

def format_html(raw_html):
    # 包一层 <root> 保证是合法结构
    soup = BeautifulSoup(f"<root>{raw_html}</root>", "html.parser")
    # Step 1: 去掉表格中的 <p>，只保留内容
    for p in soup.find_all("p"):
        if p.find_parent("td") or p.find_parent("th"):
            p.unwrap()  # 删除 <p> 标签但保留其中的文本
    # Step 2: 按块分行，表格用 prettify，其他用 strip
    lines = []
    for element in soup.root.contents:
        element_str = str(element).strip()
        if isinstance(element, Tag) and element_str:  # 只处理标签（Tag），跳过字符串
            if element.name == "table":
                # 处理表格，合并每个 <tr> 成一行
                # lines.append(element.prettify())  # 直接多行展开
                # 处理表格，合并每个 <tr> 成一行
                table_attrs = " ".join([f'{k}="{v}"' for k, v in element.attrs.items()])
                table_line = f"<table {table_attrs}>".strip()
                for tr in element.find_all("tr", recursive=False):
                    tr_html = "".join([str(td).strip() for td in tr.find_all(["td", "th"], recursive=False)])
                    table_line += f"\n<tr>{tr_html}</tr>"
                table_line += "\n</table>"
                lines.append(table_line)
            else:
                lines.append(element_str)
    # 拼接并保存
    final_html = "\n".join(lines)
    return final_html

async def convert_pdf_to_docx(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO]]:
    output_stream = StringIO() if params.is_text else BytesIO()
    logger.info(f"Converting pdf to docx...")
    cv = Converter(pdf_file=params.input_path, stream=params.input_raw)
    cv.convert(output_stream, start=0, end=None)
    cv.close()
    seek_stream(output_stream)
    output_raw = stream_to_raw(output_stream)
    return output_raw, output_stream

async def convert_docx_to_md_or_html(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO]]:
    input_path, input_raw, input_stream = params.input_path, params.input_raw, params.input_stream
    input_stream = raw_to_stream(input_raw) if not input_stream else input_stream
    if input_path and os.path.exists(input_path):
        with open(input_path, "rb") as docx_file:
            input_stream = BytesIO(docx_file.read())
    logger.info(f"Converting docx to html or markdown: {params.convert_type}...")
    if "html" in params.convert_type:
        result = mammoth.convert_to_html(input_stream)
    else:
        result = mammoth.convert_to_markdown(input_stream)
    output_html = result.value
    output_html = output_html.replace('<table>', '<table border="1">')
    # 格式化处理
    clean_html = remove_html_nested_tables(output_html)
    output_raw = format_html(clean_html)
    output_stream = raw_to_stream(output_raw)
    return output_raw, output_stream

async def convert_pdf_to_md_or_html(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO]]:
    _, docx_stream = await convert_pdf_to_docx(params)
    params = FileConvertParams(convert_type=params.convert_type, is_text=params.is_text, input_stream=docx_stream)
    output_raw, output_stream = await convert_docx_to_md_or_html(params)
    return output_raw, output_stream

async def convert_excel_and_markdown_or_html(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO]]:
    convert_type, input_raw, input_stream = params.convert_type, params.input_raw, params.input_stream
    input_stream = raw_to_stream(input_raw) if not input_stream else input_stream
    output_stream = StringIO() if params.is_text else BytesIO()
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
        output_raw = "<br><hr><br>".join(parts)
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
    return output_raw, output_stream

async def convert_to_markdown(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO]]:
    convert_type = params.convert_type
    mid = MarkItDown()
    if "2md" not in convert_type:
        raise ValueError("Only *2md conversions are supported with MarkItDown.")
    ext = convert_type.replace("2md", "").lower()
    # 安全性和鲁棒性检查
    if ext not in {"pdf", "docx", "pptx", "xlsx", "xls", "csv", "html", "json", "xml", "txt",
                   "epub", "zip", "jpg", "jpeg", "png", "mp3", "wav", "url"}:
        raise ValueError(f"Unsupported convert_type: {convert_type}")
    result = mid.convert(params.input_raw)  # 直接传入路径或 URL
    output_raw = result.text_content
    output_stream = raw_to_stream(output_raw)
    return output_raw, output_stream

async def convert_html2md(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO]]:
    if "v3" in params.convert_type:
        output_raw = Tomd(params.input_raw).markdown
        # output_raw = Tomd().convert(params.input_raw)
    elif "v2" in params.convert_type:
        output_raw = html2text.html2text(params.input_raw)
    else:
        output_raw = html2markdown.convert(params.input_raw)
    output_stream = raw_to_stream(output_raw)
    return output_raw, output_stream

async def convert_md2html(params: FileConvertParams) -> tuple[Union[str, bytes], Union[StringIO, BytesIO]]:
    if "v3" in params.convert_type:
        output_raw = mistune.markdown(params.input_raw)
    elif "v2" in params.convert_type:
        output_raw = md.markdown(params.input_raw)
    else:
        output_raw = MarkdownIt().render(params.input_raw)
    output_stream = raw_to_stream(output_raw)
    return output_raw, output_stream


