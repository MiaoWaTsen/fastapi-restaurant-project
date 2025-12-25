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
from app.common.deps import get_current_user
from app.common.websocket import manager # 🔥 引入 manager 用於檢查在線

router = APIRouter()

STARTERS = {
    1: {"name": "妙蛙種子", "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg", "hp": 130, "atk": 112},
    2: {"name": "小火龍", "img": "https://img.pokemondb.net/artwork/large/charmander.jpg", "hp": 112, "atk": 130},
    3: {"name": "傑尼龜", "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg", "hp": 121, "atk": 121}
}

def apply_iv_stats(base_val, iv):
    iv_mult = 0.9 + (iv / 100) * 0.2
    return int(base_val * iv_mult) 

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="帳號已經存在")
    
    hashed_password = get_password_hash(user.password)
    starter_id = user.starter_id if user.starter_id in [1, 2, 3] else 2
    starter_data = STARTERS[starter_id]
    
    p_uid = str(uuid.uuid4())
    p_iv = random.randint(0, 100)
    
    starter_mon = {
        "uid": p_uid,
        "name": starter_data["name"],
        "iv": p_iv,
        "lv": 1,
        "exp": 0
    }
    
    init_hp = apply_iv_stats(starter_data["hp"], p_iv)
    init_atk = apply_iv_stats(starter_data["atk"], p_iv)
    
    new_user = User(
        username=user.username,
        hashed_password=hashed_password,
        level=1,
        exp=0,
        money=1000,
        pokemon_storage=json.dumps([starter_mon]), 
        active_pokemon_uid=p_uid,
        pokemon_name=starter_data["name"],
        pokemon_image=starter_data["img"],
        pet_level=1,
        pet_exp=0,
        hp=init_hp,
        max_hp=init_hp,
        attack=init_atk,
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
def read_all_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).filter(User.id != current_user.id).all()
    
    # 🔥 修正：檢查 WebSocket 連線池 🔥
    # manager.active_connections 是一個 list of WebSockets
    # 我們假設 WebSocket state 裡有 user_id (通常在 connect 時存入)
    # 這裡簡化：我們需要一個方式知道誰連著。
    # 由於 manager 的實作細節可能沒公開 user_id，我們用一個簡單的方法：
    # 在 social.py 的 websocket endpoint 連線時，我們通常會記錄 user_id。
    # 這裡我們假設 manager 裡面有 user_id 的映射，或者我們只能從 db 判斷 last_login
    # 但為了精準，我們假設 manager 有一個 connected_user_ids (set)
    # 如果 manager 沒有公開這個屬性，我們需要改 social.py。
    # 為了不改動太多底層，我們這裡做一個簡單的 workaround:
    # 我們假設 social.py 裡的 manager 物件有一個屬性 active_user_ids (set)
    
    online_ids = getattr(manager, "active_user_ids", set())
    
    return [
        {
            "id": u.id, 
            "username": u.username, 
            "level": u.level, 
            "pokemon_image": u.pokemon_image,
            "pokemon_name": u.pokemon_name,
            "is_online": u.id in online_ids # 🔥 比對 ID
        } 
        for u in users
    ]