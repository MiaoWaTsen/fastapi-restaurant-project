# app/models/user.py

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel, ConfigDict
from app.models.base import Base

class User(Base):
    __tablename__ = "users_v9" # 🔥 改名 v9 強制更新結構

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    
    pokemon_name = Column(String(50), default="未知圖騰")
    pokemon_image = Column(String(255), default="")
    pokemon_storage = Column(String(4000), default="{}") 
    unlocked_monsters = Column(String(1000), default="")
    inventory = Column(String(4000), default="{}")
    
    # 🔥 新增：已擊敗的 Boss (逗號分隔，例如 "蚊香勇士,暴鯉龍")
    defeated_bosses = Column(String(1000), default="")

    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=10)
    
    pet_level = Column(Integer, default=1)
    pet_exp = Column(Integer, default=0)
    
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=0)
    
    quests = Column(String(4000), default="[]")

class UserCreate(BaseModel):
    username: str
    password: str
    starter_id: int

class UserRead(BaseModel):
    id: int
    username: str
    pokemon_name: str
    pokemon_image: str
    unlocked_monsters: str
    defeated_bosses: str # 新增
    quests: str
    inventory: str
    hp: int
    max_hp: int
    attack: int
    level: int 
    exp: int
    pet_level: int
    pet_exp: int
    money: int 
    
    model_config = ConfigDict(from_attributes=True)