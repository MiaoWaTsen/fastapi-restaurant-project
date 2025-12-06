# app/common/deps.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.db.session import get_db
from app.services.item_service import ItemService
from app.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM

# 定義登入網址
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def get_item_service(db: Session = Depends(get_db)) -> ItemService:
    return ItemService(db=db)

# 🔥 新增：取得當前登入的玩家 🔥
def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user