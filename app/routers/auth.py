# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User, UserCreate, UserRead
from app.core.security import get_password_hash, verify_password, create_access_token
from app.common.websocket import manager 

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# --- 🔥 御三家資料庫 (依照 PDF 修正) 🔥 ---
# 妙蛙種子: 200 HP [cite: 16]
# 小火龍: 150 HP [cite: 24]
# 傑尼龜: 160 HP [cite: 20]
STARTERS = {
    1: {
        "name": "妙蛙種子", 
        "hp": 200, 
        "atk": 8, # 基礎攻擊力先維持平衡，靠招式輸出
        "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg"
    },
    2: {
        "name": "小火龍", 
        "hp": 150, 
        "atk": 12, 
        "img": "https://img.pokemondb.net/artwork/large/charmander.jpg"
    },
    3: {
        "name": "傑尼龜", 
        "hp": 160, 
        "atk": 10, 
        "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg"
    }
}

class UserReadWithStatus(UserRead):
    is_online: bool

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

@router.get("/all", response_model=List[UserReadWithStatus])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    online_ids = manager.get_online_ids()
    results = []
    for u in users:
        u_data = UserRead.model_validate(u).model_dump()
        u_data['is_online'] = (u.id in online_ids)
        results.append(u_data)
    return results