from typing import List, Optional, Union

from pydantic import field_validator, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.config_schemas import AppConfig
from app.utils.parse import parse_config_to_model


class Settings(BaseSettings):
    env_file: str = 'app/core/configs/.env'
    model_config = SettingsConfigDict(
        env_file=env_file,
        env_file_encoding="utf-8",
        env_prefix="",  # 不需要前缀
        extra="ignore"
    )

    # 项目信息 (直接从环境变量读取)
    project_name: str
    project_description: str
    project_version: str
    # 安全密钥设置
    secret_key: str
    api_key: str
    # 令牌过期时间
    access_token_expire_minutes: int

    # 服务配置
    host: str
    port: int
    # CORS
    cors_origins: Union[str, List[str]]
    api_prefix_v1: str
    config_file: str
    whitelist_paths: List[str]

    # LLM
    # concurrency_limit: int
    mp_model_name: str
    fs_model_name: str
    wechat_mp_secret: Optional[str]
    dify_mp_secret: Optional[str]
    dify_fs_secret: Optional[str]

    # 飞书设置
    app_id: str
    app_secret: str

    # 其他设置
    max_retries: int

    # 数据库
    database_url: str

    static_root: str
    protected_manager_dir: str
    public_manager_dir: str
    temp_manager_dir: str
    static_url: str
    protected_manager_url: str
    public_manager_url: str
    temp_manager_url: str

    @field_validator("cors_origins", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """统一将字符串或列表转换为 List[str]"""
        if isinstance(v, str):
            # 处理逗号分隔的字符串（如 "a.com,b.com"）
            return [i.strip() for i in v.split(",")] if "," in v else [v]
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid CORS_ORIGINS format: {v}")

    # 延迟加载的配置
    @property
    def config(self) -> BaseModel:
        app_config = parse_config_to_model(AppConfig, self.config_file)
        return app_config


settings = Settings()

