from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import RegisterIn, LoginIn, TokenOut
from ..auth import hash_password, verify_password, make_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(409, "Email already registered")
    user=User(name=body.name.strip(), email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(user); db.commit(); db.refresh(user)
    return TokenOut(access_token=make_token(user.id), name=user.name)

@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user=db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401,"Invalid email or password")
    return TokenOut(access_token=make_token(user.id), name=user.name)
