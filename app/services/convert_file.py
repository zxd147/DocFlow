import os
from io import BytesIO, StringIO

import mammoth
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from pdf2docx import Converter

from app.models.file_params import FileConvertParams
from app.utils.file import raw_to_stream, stream_to_raw
from app.utils.logger import get_logger

logger = get_logger()

async def convert_pdf_to_docx(params: FileConvertParams):
    output_stream = StringIO() if params.is_text else BytesIO()
    logger.info(f"Converting pdf to docx...")
    cv = Converter(pdf_file=params.input_path, stream=params.input_stream)
    cv.convert(output_stream, start=0, end=None)
    cv.close()
    output_raw = stream_to_raw(output_stream)
    return output_raw, output_stream

async def convert_docx_to_md_or_html(params: FileConvertParams):
    input_path, input_stream = params.input_path, params.input_stream
    input_stream = raw_to_stream(input_stream) if input_stream else None
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

def convert_excel_to_markdown_or_html(params: FileConvertParams):
    # 读取文件为 DataFrame
    import pands as pd
    from markitdown import MarkItDown
    import pandas, openpyxl, xlrd, tabulate, markitdown
    convert_type, input_path, input_stream = params.convert_type, params.input_path, pandas.input_stream
    if isinstance(input_stream, BytesIO):
        input_stream.seek(0)
        input_stream = to_stringio(input_stream)
    csv_stream = BytesIO(csv_bytes)

    # 推荐做法：加 encoding 参数（或事先 decode 成 str 再用 StringIO）
    df = pd.read_csv(csv_stream, encoding="utf-8")
    if "csv" in convert_type:
        df = pd.read_csv(input_stream)
    elif "xls" in convert_type:
        df = pd.read_excel(input_stream, engine="openpyxl")
    elif "xlsx" in convert_type:
        df = pd.read_excel(input_stream, engine = "xlrd")
    else:
        raise ValueError(f"Unsupported convert file type: {convert_type}")
    def use_markitdown():
        # 转为 Markdown
        if "html" in convert_type:
            result = df.to_html(index=False)
        elif "md" in convert_type:
            result = df.to_markdown(index=False)
        else:
            df.to_excel("file.xlsx", index=False)

    md = MarkItDown()
    result = md.convert("input.xlsx")  # 或 input.csv
    with open("file.docx", "rb") as f:
        result = md.convert_stream(f)
    with open("output.md", "w") as f:
        f.write(result.text_content)

    return result

def convert_md2html():
    from markdown as md
    print(dir(markdown))
    file = open('help.md', 'r', encoding='utf-8').read()
    html = md.markdown(file)
    print(html)
    with open('ret.html', 'w', encoding='utf-8') as file:
        file.write(html)

    import mistune


def convert_html2md(input_path='ret.html', output_path_prefix='make'):
    converters = []
    # 方式1: html2text
    def use_html2text(html):
        import html2text
        return html2text.html2text(html)
    converters.append(('html2text', use_html2text))
    # 方式2: html2markdown
    def use_html2markdown(html):
        import html2markdown
        return html2markdown.convert(html)
    converters.append(('html2markdown', use_html2markdown))
    # 方式3: tomd
    def use_tomd(html):
        from tomd import Tomd
        return Tomd(html).markdown
    converters.append(('tomd', use_tomd))
    # 读取 HTML
    with open(input_path, 'r', encoding='utf-8') as f:
        html_text = f.read()
    # 随机选择一个转换器
    name, converter_func = random.choice(converters)
    markdown = converter_func(html_text)
    # 输出 Markdown 文件
    output_file = f'{output_path_prefix}_{name}.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f'使用 {name} 模块完成转换，输出为：{output_file}')

def convert_


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












# ---------- 示例调用 ----------
if __name__ == "__main__":
    input_pdf_path = "./2024-0.pdf"
    temp_docx_name = "2024-0.docx"
    output_html_path = "/home/agi/zxd/file/0619/000/2024-0.html"

    # 检查 PDF 文件是否存在
    if not os.path.exists(input_pdf_path):
        print(f"❌ 文件不存在: {input_pdf_path}")
    else:
        # ---------- 第一步：PDF 转 Word ----------
        convert_pdf_to_docx(input_path=input_pdf_path, output_path=temp_docx_name)
        # ---------- 第二步：Word 转 HTML ----------
        html_path, html_text, html_contents = convert_docx_to_html(input_path=temp_docx_name)
        # html_str = html_str.replace('<table>', '<table border="1">')
        # # 格式化处理
        # ---------- 第三步：去除嵌套表格 ----------
        # clean_html = remove_html_nested_tables(html_str)
        # # ---------- 第四步：格式化 HTML ----------
        # formatted_html = format_html(clean_html)
        formatted_html = html_text
        with open(output_html_path, "w", encoding="utf-8") as html_file:
            html_file.write(formatted_html)
        print(f"HTML 文件已保存至 {output_html_path}")


