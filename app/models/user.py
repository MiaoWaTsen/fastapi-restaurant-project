# app/models/user.py

from sqlalchemy import Column, Integer, String, Text, Boolean, Date
from pydantic import BaseModel, ConfigDict
from app.models.base import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users_v10" # 🔥 V2.0 全新架構

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    
    # 權限與狀態
    is_admin = Column(Boolean, default=False) # 
    is_muted = Column(Boolean, default=False) # 
    
    # 玩家數值
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=0)
    
    # 出戰寶可夢 (存放在盒子裡的唯一ID)
    active_pokemon_uid = Column(String, default="") 
    
    # 寶可夢盒子 (JSON List: [{uid, name, iv, lv, exp, ...}]) 
    pokemon_storage = Column(Text, default="[]") 
    
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
    inventory: str
    pokemon_storage: str
    active_pokemon_uid: str
    
    model_config = ConfigDict(from_attributes=True)