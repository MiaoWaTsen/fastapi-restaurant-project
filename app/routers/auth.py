# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import json
import uuid

from app.db.session import get_db
from app.models.user import User, UserCreate, UserRead
from app.common.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.common.deps import get_current_user

# 🔥 V2.11.23: 修正 Import 路徑
from app.common.game_data import POKEDEX_DATA, apply_iv_stats

router = APIRouter()

STARTERS = {
    1: "妙蛙種子",
    2: "小火龍",
    3: "傑尼龜"
}

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    starter_name = STARTERS.get(user.starter_id, "小火龍")
    starter_data = POKEDEX_DATA.get(starter_name)
    
    # 創建初始寶可夢
    starter_mon = {
        "uid": str(uuid.uuid4()),
        "name": starter_name,
        "iv": 50, # 初始 IV
        "lv": 1,
        "exp": 0
    }
    
    # 計算初始能力
    base_hp = starter_data["hp"] if starter_data else 100
    base_atk = starter_data["atk"] if starter_data else 10
    
    # 初始背包
    new_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password),
        money=300, # 初始金幣
        pokemon_name=starter_name,
        pokemon_image=starter_data["img"] if starter_data else "",
        active_pokemon_uid=starter_mon["uid"],
        pokemon_storage=json.dumps([starter_mon]),
        hp=apply_iv_stats(base_hp, 50, 1, is_hp=True),
        max_hp=apply_iv_stats(base_hp, 50, 1, is_hp=True),
        attack=apply_iv_stats(base_atk, 50, 1, is_hp=False),
        unlocked_monsters=starter_name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user