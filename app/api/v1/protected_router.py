from fastapi import APIRouter, Depends

from app.api.v1.endpoints import file_manager
from app.dependencies.auth_dependencies import bearer_auth_dependency

protected_router = APIRouter(dependencies=[Depends(bearer_auth_dependency)])

protected_router.include_router(file_manager.router, prefix="/file_manager", tags=["file"])

