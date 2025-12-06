# app/models/user.py

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel, ConfigDict
from app.models.base import Base

class User(Base):
    __tablename__ = "users_v4" # 改名重置資料庫

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    
    # 🔥 新增：寶可夢資訊 🔥
    pokemon_name = Column(String(50), default="未知圖騰")
    pokemon_image = Column(String(255), default="")
    
    # 戰鬥數值 (攻擊力調低)
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=5) # 基礎攻擊力調低
    
    # 養成與經濟
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=0)

# --- Pydantic Schemas ---
class UserCreate(BaseModel):
    username: str
    password: str
    starter_id: int # 1=草, 2=火, 3=水

class UserRead(BaseModel):
    id: int
    username: str
    pokemon_name: str # 新增
    pokemon_image: str # 新增
    hp: int
    max_hp: int
    attack: int
    level: int 
    exp: int
    money: int 
    
    model_config = ConfigDict(from_attributes=True)