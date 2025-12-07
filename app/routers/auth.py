# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List

from app.db.session import get_db
from app.models.user import User, UserCreate, UserRead
from app.core.security import get_password_hash, verify_password, create_access_token
from app.common.websocket import manager 

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

STARTERS = {
    1: { "name": "妙蛙種子", "hp": 200, "atk": 20, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg" },
    2: { "name": "小火龍", "hp": 160, "atk": 25, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg" },
    3: { "name": "傑尼龜", "hp": 180, "atk": 22, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg" }
}

LEVEL_XP = { 1: 50, 2: 100, 3: 200, 4: 350, 5: 600, 6: 1000, 7: 1800, 8: 3000 }

class UserReadWithStatus(UserRead):
    is_online: bool

# 檢查升級 (平衡修正)
def check_levelup(user):
    required_xp = LEVEL_XP.get(user.level, 999999)
    if user.exp >= required_xp:
        user.level += 1
        user.exp -= required_xp
        user.max_hp = int(user.max_hp * 1.4)
        user.hp = user.max_hp
        # 🔥 修改：攻擊力成長從 1.5 降為 1.2 🔥
        user.attack = int(user.attack * 1.2)
        return True
    return False

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    starter = STARTERS.get(user.starter_id, STARTERS[1])
    hashed_pw = get_password_hash(user.password)
    
    new_user = User(
        username=user.username, hashed_password=hashed_pw,
        pokemon_name=starter["name"], pokemon_image=starter["img"],
        # 🔥 修正：註冊時立刻解鎖圖鑑 🔥
        unlocked_monsters=starter["name"],
        hp=starter["hp"], max_hp=starter["hp"], attack=starter["atk"], money=300
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

@router.get("/me", response_model=UserRead)
def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    try:
        username = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
        if username is None: raise HTTPException(status_code=401)
    except JWTError: raise HTTPException(status_code=401)
    user = db.query(User).filter(User.username == username).first()
    if not user: raise HTTPException(status_code=401)
    return user

@router.get("/all", response_model=List[UserReadWithStatus])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    online_ids = manager.get_online_ids()
    return [{**UserRead.model_validate(u).model_dump(), 'is_online': u.id in online_ids} for u in users]