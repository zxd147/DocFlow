from typing import Dict, Any, List, Optional, Union

from pydantic import BaseModel


class LLMModelsConfig(BaseModel):
    base_url: str
    chat_endpoint: str = ""
    api_key: Optional[str] = None
    concurrency_limit: int
    timeout: int


class DifyModelsConfig(BaseModel):
    base_url: str
    chat_endpoint: str = ""
    conv_endpoint: str = ""
    api_key: Optional[str] = None
    conv_limit: int
    sort_by: str
    concurrency_limit: int
    timeout: int


class LLMParamConfig(BaseModel):
    model: str
    messages: List[Dict[str, str]] = []
    stream: bool = False
    temperature: float
    max_tokens: int
    user: str
    query: str = ""
    inputs: Dict[str, Any] = {}
    conversation_id: Optional[str] = None


class DifyParamConfig(BaseModel):
    model: str
    query: str = ""
    response_mode: str
    user: str
    conversation_id: Optional[str] = None
    inputs: Dict[str, Any] = {}
    messages: List[Dict[str, str]] = []
    stream: bool = False


class AppConfig(BaseModel):
    # 字典形式，键是模型名称
    llm_models: Dict[str, Union[LLMModelsConfig, DifyModelsConfig]]
    llm_param: Dict[str, Union[LLMParamConfig, DifyParamConfig]]

