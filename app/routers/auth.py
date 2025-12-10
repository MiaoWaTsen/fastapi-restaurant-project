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
    1: { "name": "妙蛙種子", "hp": 130, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg" },
    2: { "name": "小火龍", "hp": 112, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg" },
    3: { "name": "傑尼龜", "hp": 121, "atk": 121, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg" }
}

LEVEL_XP = { 1: 50, 2: 120, 3: 240, 4: 400, 5: 600, 6: 900, 7: 1350, 8: 2000, 9: 3000 }

class UserReadWithExp(UserRead):
    next_level_exp: int
    next_pet_level_exp: int
    is_online: bool = False

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    starter = STARTERS.get(user.starter_id, STARTERS[1])
    hashed_pw = get_password_hash(user.password)
    initial_storage = { starter["name"]: {"lv": 1, "exp": 0} }
    
    new_user = User(
        username=user.username, hashed_password=hashed_pw,
        pokemon_name=starter["name"], pokemon_image=starter["img"],
        unlocked_monsters=starter["name"],
        pokemon_storage=json.dumps(initial_storage),
        inventory="{}",
        defeated_bosses="", # 初始化
        quests="[]",
        hp=starter["hp"], max_hp=starter["hp"], attack=starter["atk"], 
        pet_level=1, pet_exp=0, level=1, exp=0, money=300
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
    
    def get_req_xp(lv): return LEVEL_XP.get(lv, 3000) if lv < 10 else 3000 + (lv - 10) * 1000

    user_dict = UserRead.model_validate(user).model_dump()
    user_dict['next_level_exp'] = get_req_xp(user.level)
    user_dict['next_pet_level_exp'] = get_req_xp(user.pet_level)
    return user_dict

@router.get("/all", response_model=List[UserReadWithExp])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    online_ids = manager.get_online_ids()
    results = []
    
    def get_req_xp(lv): return LEVEL_XP.get(lv, 3000) if lv < 10 else 3000 + (lv - 10) * 1000

    for u in users:
        u_dict = UserRead.model_validate(u).model_dump()
        u_dict['is_online'] = (u.id in online_ids)
        u_dict['next_level_exp'] = get_req_xp(u.level)
        u_dict['next_pet_level_exp'] = get_req_xp(u.pet_level)
        results.append(u_dict)
    return results