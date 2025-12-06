# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List

from app.db.session import get_db
from app.models.user import User, UserCreate, UserRead
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# --- 🔥 御三家資料庫 🔥 ---
STARTERS = {
    1: {
        "name": "妙蛙種子", 
        "hp": 120, 
        "atk": 8, 
        "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg"
    },
    2: {
        "name": "小火龍", 
        "hp": 100, 
        "atk": 12, 
        "img": "https://img.pokemondb.net/artwork/large/charmander.jpg"
    },
    3: {
        "name": "傑尼龜", 
        "hp": 110, 
        "atk": 10, 
        "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg"
    }
}

# 1. 註冊 (Sign Up) - 包含御三家選擇邏輯
@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 檢查帳號是否存在
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 取得御三家資料 (如果亂傳 ID，預設給妙蛙種子)
    starter = STARTERS.get(user.starter_id, STARTERS[1])
    
    hashed_pw = get_password_hash(user.password)
    
    # 建立新玩家 (寫入初始數值)
    new_user = User(
        username=user.username, 
        hashed_password=hashed_pw,
        
        # 寫入寶可夢資訊
        pokemon_name=starter["name"],
        pokemon_image=starter["img"],
        
        # 寫入戰鬥數值
        hp=starter["hp"],
        max_hp=starter["hp"],
        attack=starter["atk"],
        
        # 新手禮包
        money=500 
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 2. 登入 (Login)
@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# 3. 查閱自己資料
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

# 4. 🔥 新增：取得所有玩家 (給競技場用) 🔥
@router.get("/all", response_model=List[UserRead])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(User).all()