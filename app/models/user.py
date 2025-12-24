# app/models/user.py

from sqlalchemy import Column, Integer, String, Text, Boolean, Date
from pydantic import BaseModel, ConfigDict
from app.models.base import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users_v10"

    id = Column(Integer, primary_key=True, index=True)
    # 🔥 修正：加上長度限制，避免資料庫錯誤
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # 權限與狀態
    is_admin = Column(Boolean, default=False)
    is_muted = Column(Boolean, default=False)
    
    # 玩家數值
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=0)
    
    # 寵物狀態 (當前出戰)
    pokemon_name = Column(String(50), default="未知圖騰")
    pokemon_image = Column(String(255), default="")
    pet_level = Column(Integer, default=1)
    pet_exp = Column(Integer, default=0)
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=10)
    
    # 🔥 V2.0 核心欄位
    active_pokemon_uid = Column(String(100), default="") # 出戰寶可夢的 UUID
    pokemon_storage = Column(Text, default="[]")         # 盒子 (JSON List)
    
    # 遊戲資料
    inventory = Column(Text, default="{}") 
    unlocked_monsters = Column(Text, default="")
    defeated_bosses = Column(Text, default="")
    quests = Column(Text, default="[]")
    
    # 每日簽到
    last_daily_claim = Column(Date, nullable=True)
    login_days = Column(Integer, default=0)

class UserCreate(BaseModel):
    username: str
    password: str
    starter_id: int

class UserRead(BaseModel):
    id: int
    username: str
    is_admin: bool
    level: int 
    exp: int
    money: int 
    
    pokemon_name: str
    pokemon_image: str
    pet_level: int
    pet_exp: int
    hp: int
    max_hp: int
    attack: int
    
    inventory: str
    pokemon_storage: str
    active_pokemon_uid: str
    
    model_config = ConfigDict(from_attributes=True)