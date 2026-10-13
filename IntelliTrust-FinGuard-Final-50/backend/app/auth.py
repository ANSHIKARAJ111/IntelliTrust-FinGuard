from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()
ALGO = "HS256"

def hash_password(password: str) -> str:
    return pwd.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd.verify(password, hashed)

def make_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=12)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.jwt_secret, algorithm=ALGO)

def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[ALGO])
        uid = int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
