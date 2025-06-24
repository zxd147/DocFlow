import json
import xml.etree.ElementTree as ET
from typing import Type

from pydantic import BaseModel


def parse_xml(xml):
    """解析微信服务器发来的xml消息"""
    root = ET.fromstring(xml)
    msg = {}
    for child in root:
        msg[child.tag] = child.text
    return msg

def generate_reply(from_user, to_user, tim, content):
    """生成微信公众号回复消息的XML格式"""
    reply = f"""
    <xml>
      <ToUserName><![CDATA[{from_user}]]></ToUserName>
      <FromUserName><![CDATA[{to_user}]]></FromUserName>
      <CreateTime>{tim}</CreateTime>
      <MsgType><![CDATA[text]]></MsgType>
      <Content><![CDATA[{content}]]></Content>
    </xml>
    """
    return reply

# 加载配置
def parse_config_to_model(model_class: Type[BaseModel], filepath: str) -> BaseModel:
    """加载配置并返回模型实例"""
    with open(filepath) as file:
        config_dict = json.load(file)
    # 将字典的键值对解包为关键字参数
    model_config = model_class(**config_dict)
    return model_config

