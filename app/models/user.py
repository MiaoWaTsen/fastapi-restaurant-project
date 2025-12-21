# app/models/user.py

from sqlalchemy import Column, Integer, String, Text
from pydantic import BaseModel, ConfigDict
from app.models.base import Base

class User(Base):
    # 🔥 關鍵：必須保留這個名稱，你的存檔才不會不見！
    __tablename__ = "users_v9" 

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    
    pokemon_name = Column(String(50), default="未知圖騰")
    pokemon_image = Column(String(255), default="")
    pokemon_storage = Column(Text, default="{}") 
    unlocked_monsters = Column(Text, default="")
    inventory = Column(Text, default="{}")
    defeated_bosses = Column(Text, default="")

    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=10)
    
    pet_level = Column(Integer, default=1)
    pet_exp = Column(Integer, default=0)
    
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=0)
    
    quests = Column(Text, default="[]")

# Pydantic Models (保留你的設定)
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
    defeated_bosses: str
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