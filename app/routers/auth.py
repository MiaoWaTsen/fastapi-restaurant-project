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
# 這裡需要從 shop 導入資料來設定初始精靈
from app.routers.shop import POKEDEX_DATA

router = APIRouter()

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 初始化精靈 (預設皮卡丘，或者你可以改成御三家選擇邏輯)
    starter_name = "皮卡丘" 
    starter_data = POKEDEX_DATA.get(starter_name)
    starter_img = starter_data["img"] if starter_data else ""
    
    new_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password),
        pokemon_name=starter_name,
        pokemon_image=starter_img,
        pokemon_storage=json.dumps([{
            "uid": str(uuid.uuid4()),
            "name": starter_name,
            "iv": 50,
            "lv": 1,
            "exp": 0
        }]),
        active_pokemon_uid="" # 這裡可以隨後設置
    )
    # 設定第一隻為活躍
    box = json.loads(new_user.pokemon_storage)
    new_user.active_pokemon_uid = box[0]["uid"]
    
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