# app/models/user.py

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel, ConfigDict
# ⚠️ 只能匯入這個！
from app.models.base import Base

class User(Base):
    __tablename__ = "users_v3"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    
    hp = Column(Integer, default=200)
    max_hp = Column(Integer, default=200)
    attack = Column(Integer, default=20)
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=0)

# --- Pydantic Schemas ---
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
    money: int 
    
    model_config = ConfigDict(from_attributes=True)