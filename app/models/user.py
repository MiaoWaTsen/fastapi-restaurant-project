# app/models/user.py

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel, ConfigDict
# ⚠️ 關鍵：也是從共用的 base.py 匯入 Base
from app.models.base import Base

# --- 1. 資料庫食譜 (SQLAlchemy) ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False) # 這裡存加密過的亂碼，不是明碼
    
    # 玩家也有戰鬥數值！(為了之後的 PVP 或 PVE)
    hp = Column(Integer, default=200)
    max_hp = Column(Integer, default=200)
    attack = Column(Integer, default=20)


# --- 2. 菜單 (Pydantic Schemas) ---

# 註冊時只要填這兩個
class UserCreate(BaseModel):
    username: str
    password: str

# 讀取玩家資料時，回傳這些 (絕對不能回傳 password!)
class UserRead(BaseModel):
    id: int
    username: str
    hp: int
    max_hp: int
    attack: int
    
    # Pydantic V2 設定
    model_config = ConfigDict(from_attributes=True)