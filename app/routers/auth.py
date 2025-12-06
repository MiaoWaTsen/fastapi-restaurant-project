# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User, UserCreate, UserRead
from app.core.security import get_password_hash, verify_password, create_access_token
# 引入廣播站長來查名單
from app.common.websocket import manager 

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

STARTERS = {
    1: {"name": "妙蛙種子", "hp": 120, "atk": 8, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg"},
    2: {"name": "小火龍", "hp": 100, "atk": 12, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg"},
    3: {"name": "傑尼龜", "hp": 110, "atk": 10, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg"}
}

# --- 定義一個包含「在線狀態」的新格式 ---
class UserReadWithStatus(UserRead):
    is_online: bool

# ... (register, login, me 保持不變，省略以節省篇幅，請保留原有的程式碼) ...
# 如果你怕覆蓋錯，請只替換下面的 get_all_users，並確保上面的 import 有加

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user: raise HTTPException(status_code=400, detail="Username already registered")
    starter = STARTERS.get(user.starter_id, STARTERS[1])
    hashed_pw = get_password_hash(user.password)
    new_user = User(
        username=user.username, hashed_password=hashed_pw,
        pokemon_name=starter["name"], pokemon_image=starter["img"],
        hp=starter["hp"], max_hp=starter["hp"], attack=starter["atk"], money=500
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserRead)
def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError: raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.username == username).first()
    if user is None: raise HTTPException(status_code=401, detail="User not found")
    return user

# 🔥 修改：回傳包含在線狀態的列表 🔥
@router.get("/all", response_model=List[UserReadWithStatus])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    # 問站長：現在誰在線上？
    online_ids = manager.get_online_ids()
    
    results = []
    for u in users:
        # 把資料轉成字典，並多加一個 is_online 欄位
        u_data = UserRead.model_validate(u).model_dump()
        u_data['is_online'] = (u.id in online_ids)
        results.append(u_data)
        
    return results