import hashlib
import re
import time
from pathlib import Path
from string import Template
from typing import List
from typing import Union

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.core.configs.settings import settings
from app.utils.file import async_save_string_or_bytes_to_path, \
    get_bytes_from_base64, local_path_to_url
from app.utils.logger import get_logger

logger = get_logger()

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Document</title>
</head>
<body>
$body
</body>
</html>""")

# async def remove_html_nested_tables(raw_html):
#     soup = BeautifulSoup(raw_html, "html.parser")
#     # 找出所有 table
#     all_tables = soup.find_all("table")
#     for table in all_tables:
#         # 如果 table 有父级是 table，则为嵌套
#         if table.find_parent("table"):
#             # 用 table 的 children 直接替换整个 table 标签
#             # table.unwrap()  # unwrap 会移除标签但保留内容
#             text = table.get_text(strip=True)  # separator=" ",
#             # text = text.replace("\n", " ").replace("  ", " ")
#             from bs4.element import NavigableString
#             table.replace_with(NavigableString(text))
#         else:
#             # 非嵌套表格 → 设置 border 属性（如未设置）
#             if not table.has_attr("border"):
#                 table["border"] = "1"
#     final_html = str(soup)
#     return final_html

def split_texts(texts: Union[str, List[str]], min_tokens: int = 20, max_tokens: int = 100) -> List[List[str]]:
    def split_text(text: str, sentences: List[str]) -> List[str]:
        if len(text) <= max_tokens:
            # 如果文本长度不超过100个字，则不需要断句
            sentences.append(text) if text.strip() else None
            return sentences
        start, mid, end = min_tokens, (len(text)) // 2 , min(max_tokens, len(text) - min_tokens)
        mid = max(start, min(mid, end))  # 保证在正常范围内
        reverse = False if len(text) <= min_tokens + max_tokens else True
        cut_text = text[mid:end]
        punc = get_punctuation(cut_text)
        index = get_punc_index(text, punc, start, mid, end, reverse=reverse)
        # 按照找到的位置分割文本
        first_sentence = text[:index + 1]
        second_sentence = text[index + 1:]
        sentences.append(first_sentence)
        sentences = split_text(second_sentence, sentences)
        return sentences
    assert min_tokens <= max_tokens, f"Invalid range: min_tokens={min_tokens}, max_tokens={max_tokens}"
    texts = [texts] if isinstance(texts, str) else texts
    all_sentences = []
    for one_text in texts:
        one_sentences = split_text(one_text, [])
        all_sentences.append(one_sentences)
    return all_sentences

def get_punctuation(text):
    punctuation_groups = [
        [':', '：'],
        ['.', '!', '?','。',  '！', '？'],
        [';', '；'],
        [',', '，', '、']
    ]
    text_set = set(text)
    for group in punctuation_groups:
        if text_set & set(group):
            return group
    return [p for group in punctuation_groups for p in group]

def search_punc(text, punctuation, start, end, step):
    for i in range(start, end, step):
        if text[i] in punctuation:
            return i
    return None

def get_punc_index(text, punctuation, start, mid, end, reverse=False) -> int:
    if reverse:
        idx = search_punc(text, punctuation, end - 1, start - 1, -1)
        return idx if idx is not None else end - 1
    else:
        idx = search_punc(text, punctuation, mid, end, 1)
        if idx is not None:
            return idx
        idx = search_punc(text, punctuation, mid - 1, start - 1, -1)
        return idx if idx is not None else end - 1

async def strip_markdown(text: str) -> str:
    # 1. 去除标题符号（如 # 一级标题）
    text = re.sub(r'(^|\n)#{1,6}\s+', r'\1', text)
    # 2. 图片语法：![alt](url) -> alt url
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'\1 \2', text)  # type: ignore
    # 3. 链接语法：[text](url) -> text url
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 \2', text)
    # 4. 加粗/斜体处理
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # 5. 行内代码
    text = re.sub(r'`([^`]*)`', r'\1', text)
    # 6. 无序列表前缀
    text = re.sub(r'^[\*\-\+] +', '', text, flags=re.MULTILINE)
    # 7. 删除表格分隔线
    text = re.sub(r'^\|? *[-| ]+ *\|?$', '', text, flags=re.MULTILINE)
    # 8. 表格竖线 -> 空格
    text = re.sub(r'\|', ' ', text)
    # 9. 压缩空行
    text = re.sub(r'\n{2,}', '\n', text)
    # 10. 去首尾空白
    text = text.strip()
    return text

async def handle_base64_image(img, policy, images_dir) -> None:
    """处理 base64 图片，根据 policy 返回修改后的 img 标签"""
    src = img.get("src", "")
    if not src.startswith("data:image"):
        return
    if policy == 'remove':
        img.decompose()
    elif policy == 'base64':
        pass  # 保留原始 base64
    else:
        image_raw, _, image_ext = get_bytes_from_base64(src)
        ext = image_ext or '.jpg'
        hash_name = hashlib.md5(image_raw).hexdigest()
        save_path = Path(images_dir) / f"{hash_name}{ext}"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path = str(save_path).replace("\\", "/")
        await async_save_string_or_bytes_to_path(image_raw, save_path)

        img["alt"] = f"image_{hash_name}"
        if policy == 'path':
            img["src"] = save_path
        elif policy == 'url':
            save_url = local_path_to_url(save_path, settings.static_url, settings.static_root)
            img["src"] = save_url

def flatten_table(element: Tag) -> str:
    """将单层非嵌套表格展平为紧凑结构"""
    if not element.has_attr("border"):
        element["border"] = "1"
    table_attrs = " ".join([f'{k}="{v}"' for k, v in element.attrs.items()])
    table_line = f"<table {table_attrs}>".strip()
    for tr in element.find_all("tr", recursive=False):
        tr_html = "".join([str(td).strip() for td in tr.find_all(["td", "th"], recursive=False)])
        table_line += f"\n<tr>{tr_html}</tr>"
    table_line += "\n</table>"
    return table_line

async def format_html(raw_html, policy, images_dir) -> str:
    """格式化 HTML，包括去嵌套表格、去 <p>、加 border 等"""
    soup = BeautifulSoup(f"<root>{raw_html}</root>", "html.parser")
    # Step 1: 去掉表格中的 <p>
    for p in soup.find_all("p"):
        if p.find_parent("td") or p.find_parent("th"):
            p.unwrap()
    # Step 2: 处理 base64 图片
    for img in soup.find_all("img"):
        await handle_base64_image(img, policy, images_dir)
    # Step 3: 遍历顶层元素，结构化处理
    lines = []
    for element in soup.root.contents:
        element_str = str(element).strip()
        if isinstance(element, Tag) and element_str:
            if element.name == "table":
                if element.find_parent("table"):
                    # 嵌套表格 → 转为纯文本（逻辑保留原位，因为这步依赖前文结构清洗）
                    text = element.get_text(strip=True)
                    lines.append(text)
                else:
                    lines.append(flatten_table(element))
            else:
                lines.append(element_str)
    final_html = "\n".join(lines)
    full_html = HTML_TEMPLATE.substitute(body=final_html)
    return full_html


if __name__ == "__main__":
    # 测试
    test_text = (
        "在夜幕降临之际星星闪烁着微光月亮静静地悬挂在天空."
        "一阵微风拂过树叶沙沙作响似乎说着未来的故事!"
        "远处传来了狗的吠叫声,一只猫悄悄地溜进了黑暗的角落，"
        "突然闪电划破了夜空随之而来的是雷声的轰鸣！"
        "雨滴敲打着窗户节奏有序而明快在这样的夜晚任何故事都有可能发生任何梦想都有可能实现。"
    )
    # with open("content_1600.txt") as f:
    # with open("exam_1000.txt") as f:
    #     test_text = f.read()  #  680 微秒/次，  1240 微秒/5次
    test_texts = [test_text] * 5
    split_min_tokens = 20
    split_max_tokens = 100
    start_time = time.perf_counter()
    sens = split_texts(test_texts, split_min_tokens, split_max_tokens)
    end_time = time.perf_counter()
    for sen in sens:
        print(f"sen:{sen}\n")
    print(f"Execution time: {end_time - start_time} seconds")   # 1次约 37微秒, 5次 145 微秒


