# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List
import json

from app.db.session import get_db
from app.models.user import User, UserCreate, UserRead
from app.core.security import get_password_hash, verify_password, create_access_token
from app.common.websocket import manager 

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

STARTERS = {
    1: { "name": "妙蛙種子", "hp": 220, "atk": 105, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg" },
    2: { "name": "小火龍", "hp": 180, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg" },
    3: { "name": "傑尼龜", "hp": 200, "atk": 110, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg" }
}

# 經驗值表 (通用)
LEVEL_XP = { 1: 50, 2: 100, 3: 200, 4: 350, 5: 600, 6: 1000, 7: 1800, 8: 3000, 9: 5000, 10: 8000 }

class UserReadWithExp(UserRead):
    next_level_exp: int      # 玩家升級所需
    next_pet_level_exp: int  # 寶可夢升級所需
    is_online: bool = False

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    starter = STARTERS.get(user.starter_id, STARTERS[1])
    hashed_pw = get_password_hash(user.password)
    
    # 初始倉庫
    initial_storage = {
        starter["name"]: {"lv": 1, "exp": 0}
    }
    
    new_user = User(
        username=user.username, hashed_password=hashed_pw,
        pokemon_name=starter["name"], pokemon_image=starter["img"],
        unlocked_monsters=starter["name"],
        pokemon_storage=json.dumps(initial_storage), # 存入倉庫
        
        hp=starter["hp"], max_hp=starter["hp"], attack=starter["atk"], 
        
        pet_level=1, pet_exp=0, # 寶可夢初始
        level=1, exp=0,         # 玩家初始
        money=300
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
    return {"access_token": create_access_token(data={"sub": user.username}), "token_type": "bearer"}

@router.get("/me", response_model=UserReadWithExp)
def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    try:
        username = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
        if username is None: raise HTTPException(status_code=401)
    except JWTError: raise HTTPException(status_code=401)
    
    user = db.query(User).filter(User.username == username).first()
    if not user: raise HTTPException(status_code=401)
    
    user_dict = UserRead.model_validate(user).model_dump()
    # 填充兩個經驗條上限
    user_dict['next_level_exp'] = LEVEL_XP.get(user.level, 999999)
    user_dict['next_pet_level_exp'] = LEVEL_XP.get(user.pet_level, 999999)
    
    return user_dict

@router.get("/all", response_model=List[UserReadWithExp])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    online_ids = manager.get_online_ids()
    results = []
    for u in users:
        u_dict = UserRead.model_validate(u).model_dump()
        u_dict['is_online'] = (u.id in online_ids)
        u_dict['next_level_exp'] = LEVEL_XP.get(u.level, 999999)
        u_dict['next_pet_level_exp'] = LEVEL_XP.get(u.pet_level, 999999)
        results.append(u_dict)
    return results