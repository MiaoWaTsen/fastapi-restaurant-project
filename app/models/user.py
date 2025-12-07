# app/models/user.py

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel, ConfigDict
from app.models.base import Base

class User(Base):
    __tablename__ = "users_v5" # 🔥 改名 v5 強制更新結構

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    
    pokemon_name = Column(String(50), default="未知圖騰")
    pokemon_image = Column(String(255), default="")
    
    # 🔥 新增：已解鎖圖鑑 (用逗號分隔字串儲存，例: "皮卡丘,小火龍")
    unlocked_monsters = Column(String(1000), default="")

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
    unlocked_monsters: str # 新增
    hp: int
    max_hp: int
    attack: int
    level: int 
    exp: int
    money: int 
    
    model_config = ConfigDict(from_attributes=True)