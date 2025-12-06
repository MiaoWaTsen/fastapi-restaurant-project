# app/models/user.py

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel, ConfigDict
from app.models.base import Base

class User(Base):
    # 🔥 改名為 v3，強迫資料庫更新結構 (加入 money)
    __tablename__ = "users_v3"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    
    # 戰鬥數值
    hp = Column(Integer, default=200)
    max_hp = Column(Integer, default=200)
    attack = Column(Integer, default=20)
    
    # 養成數值
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    
    # 🔥 新增：經濟系統 (錢包) 🔥
    money = Column(Integer, default=0)


# --- Pydantic Schemas (出貨單) ---

class UserCreate(BaseModel):
    username: str
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    hp: int
    max_hp: int
    attack: int
    level: int 
    exp: int
    # 🔥 記得要把錢包也放進出貨單，前端才看得到！
    money: int 
    
    model_config = ConfigDict(from_attributes=True)