# app/models/item.py

from sqlalchemy import Column, Integer, String, Text
from pydantic import BaseModel, ConfigDict
from typing import Optional
# ⚠️ 只能匯入這個！絕對不要在這裡匯入 User 或 Service 或 Router！
from app.models.base import Base

class Item(Base):
    __tablename__ = "monsters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    
    hp = Column(Integer, nullable=False, default=100)
    max_hp = Column(Integer, nullable=False, default=100)
    attack = Column(Integer, nullable=False, default=10)

# --- Pydantic Schemas ---
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    hp: int = 100
    max_hp: int = 100
    attack: int = 10

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    attack: Optional[int] = None

class ItemRead(ItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)