import os

import mammoth
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from pdf2docx import Converter


def pdf_to_docx(pdf_path, docx_path):
    print(f"正在将 {pdf_path} 转换为 Word 文件...")
    cv = Converter(pdf_path)
    cv.convert(docx_path, start=0, end=None)
    cv.close()
    print(f"Word 文件已保存至 {docx_path}")

def docx_to_html(docx_path):
    print(f"正在将 {docx_path} 转换为 HTML...")
    with open(docx_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
    html_content = result.value
    return html_content

# ---------- 第三步：去除嵌套表格 ----------
def remove_nested_tables(raw_html):
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
        pdf_to_docx(input_pdf_path, temp_docx_name)
        # ---------- 第二步：Word 转 HTML ----------
        html_str = docx_to_html(temp_docx_name)
        html_str = html_str.replace('<table>', '<table border="1">')
        # 格式化处理
        clean_html = remove_nested_tables(html_str)
        # ---------- 第四步：格式化 HTML ----------
        formatted_html = format_html(clean_html)
        with open(output_html_path, "w", encoding="utf-8") as html_file:
            html_file.write(formatted_html)
        print(f"HTML 文件已保存至 {output_html_path}")


