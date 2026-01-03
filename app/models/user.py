# app/models/user.py

from sqlalchemy import Column, Integer, String, Text, Boolean
from pydantic import BaseModel, ConfigDict
from app.db.base_class import Base

class User(Base):
    # 🔥 強制建立新表格，清除所有舊資料與Bug
    __tablename__ = "users_v11"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # 權限
    is_admin = Column(Boolean, default=False)
    
    # 玩家數值
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=300) # 初始 300G
    
    # 寵物狀態 (預設小火龍)
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
    
    # ❌ 已移除簽到欄位

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