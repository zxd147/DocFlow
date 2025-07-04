import time
from typing import List, Union


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

def get_punc_index(text, punctuation, start, mid, end, reverse=False):
    if reverse:
        idx = search_punc(text, punctuation, end - 1, start - 1, -1)
        return idx if idx is not None else end - 1
    else:
        idx = search_punc(text, punctuation, mid, end, 1)
        if idx is not None:
            return idx
        idx = search_punc(text, punctuation, mid - 1, start - 1, -1)
        return idx if idx is not None else end - 1


if __name__ == "__main__":
    # 测试
    text = (
        "在夜幕降临之际星星闪烁着微光月亮静静地悬挂在天空."
        "一阵微风拂过树叶沙沙作响似乎说着未来的故事!"
        "远处传来了狗的吠叫声,一只猫悄悄地溜进了黑暗的角落，"
        "突然闪电划破了夜空随之而来的是雷声的轰鸣！"
        "雨滴敲打着窗户节奏有序而明快在这样的夜晚任何故事都有可能发生任何梦想都有可能实现。"
    )
    # with open("content_1600.txt") as f:
    with open("exam_1000.txt") as f:
        text = f.read()  #  680 微秒/次，  1240 微秒/5次
    texts = [text] * 5
    min_tokens = 20
    max_tokens = 100
    start_time = time.perf_counter()
    sens = split_texts(texts, min_tokens, max_tokens)
    end_time = time.perf_counter()
    for sen in sens:
        print(f"sen:{sen}\n")
    print(f"Execution time: {end_time - start_time} seconds")   # 1次约 37微秒, 5次 145 微秒


