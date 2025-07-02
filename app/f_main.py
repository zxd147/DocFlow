import json
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Path, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.configs.settings import settings
from app.core.lifespan import lifespan
from app.dependencies.auth_dependencies import bearer_auth_dependency
from app.middlewares.log_middleware import log_request_middleware
from app.utils.status import get_system_status


def create_app() -> FastAPI:
    init_app = FastAPI(title=settings.project_name, description=settings.project_description, version=settings.project_version,
        openapi_url=f"{settings.api_prefix_v1}/openapi.json", docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)
    init_app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])  # 设置CORS
    init_app.middleware("http")(log_request_middleware)
    init_app.mount("/static/public", StaticFiles(directory="app/static/public"), name="public-static")
    init_app.mount("/static/temp", StaticFiles(directory="app/static/temp"), name="temp-static")
    # 添加请求日志中间件 - 简化版，不读取请求体
    init_app.include_router(api_router, prefix=settings.api_prefix_v1)  # 注册API路由
    return init_app

app = create_app()

@app.get("/static/protected/{file_path:path}")
async def protected_static(file_path: str, _: None = Depends(bearer_auth_dependency)):
    protected_dir = Path(settings.protected_manager_dir).resolve()
    protected_file_path = (protected_dir / file_path).resolve()
    try:
        protected_file_path.relative_to(protected_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access outside permitted directory is forbidden")
    if not protected_file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=protected_file_path)

@app.api_route("/", methods=["GET", "POST"])
async def index(request: Request):
    """前端页面入口"""
    if request.method == "GET":
        index_html = "app/static/index.html"
        return FileResponse(index_html)
    elif request.method == "POST":
        index_data = {"message": "OpenAPI is running..."}
        return JSONResponse(content=index_data, status_code=200)

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico", headers={"Cache-Control": "public, max-age=3600"})

@app.api_route("/health", methods=["GET", "POST"])
@app.api_route("/http_check", methods=["GET", "POST"])
async def health():
    """Health check."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    health_data = {"status": "healthy", "timestamp": timestamp}
    # 返回JSON格式的响应
    return JSONResponse(content=health_data, status_code=200)

@app.get("/status")
def fetch_system_status():
    """获取电脑运行状态"""
    status_data = get_system_status()
    status_json = json.dumps(status_data, indent=4, ensure_ascii=False)
    return Response(content=status_json, media_type="application/json")

@app.get("/monitor")
async def monitor_system_status():
    """获取电脑运行状态"""
    monitor_html = "app/static/monitor.html"
    return FileResponse(monitor_html)

if __name__ == "__main__":
    host = settings.host
    port = settings.port
    uvicorn.run("app.f_main:app", host=host, port=port, reload=True)
