# app/models/user.py

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel, ConfigDict
from app.models.base import Base

class User(Base):
    __tablename__ = "users_v7" # 🔥 改名 v7 強制更新結構

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    
    # 當前寶可夢外觀
    pokemon_name = Column(String(50), default="未知圖騰")
    pokemon_image = Column(String(255), default="")
    
    # 倉庫：存儲所有寶可夢的狀態
    # 格式: {"皮卡丘": {"lv": 5, "exp": 100}, "小火龍": {"lv": 1, "exp": 0}}
    pokemon_storage = Column(String(4000), default="{}") 
    unlocked_monsters = Column(String(1000), default="") # 舊欄位保留做快速查詢

    # 當前寶可夢數值
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=10)
    
    # 🔥 雙等級系統 🔥
    pet_level = Column(Integer, default=1) # 寶可夢等級
    pet_exp = Column(Integer, default=0)   # 寶可夢經驗
    
    level = Column(Integer, default=1)     # 玩家(訓練師)等級
    exp = Column(Integer, default=0)       # 玩家經驗
    money = Column(Integer, default=0)
    
    quests = Column(String(4000), default="[]")

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
    quests: str
    hp: int
    max_hp: int
    attack: int
    # 回傳雙等級
    level: int 
    exp: int
    pet_level: int
    pet_exp: int
    money: int 
    
    model_config = ConfigDict(from_attributes=True)