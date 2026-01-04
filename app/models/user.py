# app/models/user.py

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from pydantic import BaseModel, ConfigDict
from app.db.base_class import Base
from datetime import datetime

# =================================================================
# 1. 玩家模型 (User)
# =================================================================
class User(Base):
    __tablename__ = "users_v11"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # 權限
    is_admin = Column(Boolean, default=False)
    
    # 玩家數值
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=300)
    
    # 寵物狀態 (當前出戰)
    pokemon_name = Column(String(50), default="小火龍")
    pokemon_image = Column(String(255), default="https://img.pokemondb.net/artwork/large/charmander.jpg")
    pet_level = Column(Integer, default=1)
    pet_exp = Column(Integer, default=0)
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=10)
    
    # 核心資料
    active_pokemon_uid = Column(String(100), default="") 
    pokemon_storage = Column(Text, default="[]") 
    
    # 遊戲資料
    inventory = Column(Text, default="{}") 
    unlocked_monsters = Column(Text, default="")
    quests = Column(Text, default="[]")

# =================================================================
# 2. 道館模型 (Gym) - 更新版
# =================================================================
class Gym(Base):
    __tablename__ = "gyms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    buff_desc = Column(String)
    income_rate = Column(Integer) # Gold per minute
    
    leader_id = Column(Integer, ForeignKey("users_v11.id"), nullable=True)
    occupied_at = Column(DateTime, nullable=True)
    protection_until = Column(DateTime, nullable=True) 
    
    # 鏡像數據
    leader_name = Column(String, default="")
    leader_pokemon = Column(String, default="") 
    
    # 🔥 新增：紀錄守塔寶可夢的 UID
    leader_pokemon_uid = Column(String, default="")
    
    leader_hp = Column(Integer, default=0)
    leader_max_hp = Column(Integer, default=0)
    leader_atk = Column(Integer, default=0)
    leader_img = Column(String, default="")

# Pydantic Schemas
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