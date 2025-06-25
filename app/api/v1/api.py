from fastapi import APIRouter

from app.api.v1.protected_router import protected_router
from app.api.v1.public_router import public_router

api_router = APIRouter()
# 添加各个端点路由
api_router.include_router(public_router)
api_router.include_router(protected_router)
