from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.configs.settings import settings

bearer_scheme = HTTPBearer()

def bearer_auth_dependency(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    token = credentials.credentials
    if token != settings.secret_key:
        raise HTTPException(status_code=401,
                            detail="Unauthorized: Invalid or missing credentials",
                            headers={'WWW-Authenticate': 'Bearer realm="Secure Area"'})
    # 认证成功可以返回用户信息或None
    return None

