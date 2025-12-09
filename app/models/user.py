# app/models/user.py

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel, ConfigDict
from app.models.base import Base

class User(Base):
    __tablename__ = "users_v6" # 🔥 改名 v6 強制更新結構

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    
    pokemon_name = Column(String(50), default="未知圖騰")
    pokemon_image = Column(String(255), default="")
    unlocked_monsters = Column(String(1000), default="")

    # 🔥 新增：任務清單 (JSON字串)
    # 格式: [{"target":"卡拉卡拉", "req":3, "now":0, "gold":200, "xp":100, "status":"WAITING"}, ...]
    quests = Column(String(4000), default="[]") 

    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=5)
    
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=0)

# --- Pydantic ---
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
    quests: str # 新增
    hp: int
    max_hp: int
    attack: int
    level: int 
    exp: int
    money: int 
    
    model_config = ConfigDict(from_attributes=True)