import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, constr
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth import pwd_context, SECRET_KEY, ALGORITHM
from config import get_db, RoleModel, UserModel

router = APIRouter(prefix="/api", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: constr(strip_whitespace=True, min_length=3, max_length=100)
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    role: Optional[constr(strip_whitespace=True, to_lower=True)] = "editor"


class AuthUserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: AuthUserResponse


@router.post("/auth/register", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    role_name = payload.role if payload.role in ("admin", "editor") else "editor"
    role = db.query(RoleModel).filter(RoleModel.name == role_name).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="System role configuration is missing.")

    existing_user = db.query(UserModel).filter(
        or_(UserModel.username == payload.username, UserModel.email == payload.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already exists.")

    hashed_password = pwd_context.hash(payload.password)
    user = UserModel(
        username=payload.username,
        email=payload.email,
        password_hash=hashed_password,
        role_id=role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role.name,
    }


@router.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    login_identifier = form_data.username.strip()
    user = db.query(UserModel).filter(
        or_(UserModel.username == login_identifier, UserModel.email == login_identifier)
    ).first()

    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password.")

    role_name = user.role_rel.name if user.role_rel else None
    if not role_name:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User role configuration error.")

    token = jwt.encode(
        {
            "sub": user.username,
            "id": user.id,
            "user_id": user.id,
            "email": user.email,
            "role": role_name,
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role_name,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": role_name,
        },
    }
