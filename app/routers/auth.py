# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import json
import uuid
import random

from app.db.session import get_db
from app.models.user import User, UserCreate, UserRead
from app.core.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

# 簡單的御三家資料 (避免循環引用 shop.py)
STARTERS = {
    1: {"name": "妙蛙種子", "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg", "hp": 130, "atk": 112},
    2: {"name": "小火龍", "img": "https://img.pokemondb.net/artwork/large/charmander.jpg", "hp": 112, "atk": 130},
    3: {"name": "傑尼龜", "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg", "hp": 121, "atk": 121}
}

# 天賦計算公式 (複製自 shop.py 以確保初始數值正確)
def apply_iv_stats(base_val, iv):
    iv_mult = 0.9 + (iv / 100) * 0.2
    return int(base_val * iv_mult) # Lv.1 成長係數為 1

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 1. 檢查帳號是否重複
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="帳號已經存在")
    
    # 2. 密碼加密
    hashed_password = get_password_hash(user.password)
    
    # 3. 準備初始寶可夢 (V2.0 邏輯)
    starter_id = user.starter_id if user.starter_id in [1, 2, 3] else 2 # 預設小火龍
    starter_data = STARTERS[starter_id]
    
    # 生成唯一 ID 與 天賦 IV
    p_uid = str(uuid.uuid4())
    p_iv = random.randint(0, 100)
    
    # 建立第一隻寶可夢物件
    starter_mon = {
        "uid": p_uid,
        "name": starter_data["name"],
        "iv": p_iv,
        "lv": 1,
        "exp": 0
    }
    
    # 計算初始能力值 (含 IV 加成)
    init_hp = apply_iv_stats(starter_data["hp"], p_iv)
    init_atk = apply_iv_stats(starter_data["atk"], p_iv)
    
    # 4. 建立玩家資料
    new_user = User(
        username=user.username,
        hashed_password=hashed_password,
        level=1,
        exp=0,
        money=1000, # 初始金幣
        
        # V2.0 核心欄位
        pokemon_storage=json.dumps([starter_mon]), # 存為列表
        active_pokemon_uid=p_uid,
        
        # 當前出戰狀態
        pokemon_name=starter_data["name"],
        pokemon_image=starter_data["img"],
        pet_level=1,
        pet_exp=0,
        hp=init_hp,
        max_hp=init_hp,
        attack=init_atk,
        
        # 其他初始化
        inventory=json.dumps({}),
        unlocked_monsters=starter_data["name"],
        is_admin=False
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
            detail="帳號或密碼錯誤",
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

@router.get("/all")
def read_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    # 為了安全和傳輸量，只回傳必要欄位
    return [
        {
            "id": u.id, 
            "username": u.username, 
            "level": u.level, 
            "pokemon_image": u.pokemon_image,
            "pokemon_name": u.pokemon_name,
            "is_online": False # 簡化處理，如果要即時在線需搭配 Redis 或 Memory
        } 
        for u in users
    ]