import jwt
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from config import UserModel

import os
import bcrypt

# Fix incompatibility between passlib 1.7.4 detect_wrap_bug and modern bcrypt >= 4.0
# where passlib tests a 255-byte secret that bcrypt strictly rejects.
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("About", (), {"__version__": getattr(bcrypt, "__version__", "4.0.0")})()

_orig_bcrypt_hashpw = bcrypt.hashpw
def _patched_bcrypt_hashpw(password, salt):
    if isinstance(password, bytes) and len(password) > 72:
        password = password[:72]
    elif isinstance(password, str) and len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72]
    return _orig_bcrypt_hashpw(password, salt)
bcrypt.hashpw = _patched_bcrypt_hashpw

SECRET_KEY = os.getenv("JWT_SECRET", "change-this-secret-in-production-use-a-strong-key")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

class TokenData(BaseModel):
    id: int = 1
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    username: str
    role: str

def _is_demo_auth_enabled() -> bool:
    return (
        os.getenv("DEMO_AUTH_ENABLED", "").lower() == "true" and
        os.getenv("ENVIRONMENT", "").lower() == "development"
    )

def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        if _is_demo_auth_enabled():
            return TokenData(id=1, username="DemoAdmin", email="admin@demo.local", role="admin")
        raise HTTPException(status_code=401, detail="Not authenticated")

    if token == "dummy-admin-token":
        if _is_demo_auth_enabled():
            return TokenData(id=1, username="DemoAdmin", email="admin@demo.local", role="admin")
        raise HTTPException(status_code=401, detail="Demo authentication is disabled")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id") or payload.get("user_id") or 1
        return TokenData(
            id=int(user_id),
            username=payload.get("sub"),
            email=payload.get("email"),
            role=payload.get("role")
        )
    except jwt.PyJWTError:
        if _is_demo_auth_enabled():
            return TokenData(id=1, username="DemoAdmin", role="admin")
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(allowed_roles: List[str]):
    def role_checker(user: TokenData = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Access Denied")
        return user
    return role_checker