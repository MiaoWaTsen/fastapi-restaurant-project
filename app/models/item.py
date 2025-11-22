# app/models/item.py

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel, ConfigDict 
from typing import Optional 

Base = declarative_base()

# --- 1. 修改倉庫食譜 (SQLAlchemy) ---
class Item(Base):
    __tablename__ = "items" 

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # 新增這一行！
    # nullable=False 代表這個欄位「必填」，不能是空的
    price = Column(Integer, nullable=False) 


# --- 2. 修改菜單 (Pydantic) ---
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    # 新增這一行！(基礎菜單就要有價格)
    price: int 

class ItemCreate(ItemBase):
    pass 

class ItemUpdate(ItemBase):
    name: Optional[str] = None
    description: Optional[str] = None
    # 新增這一行！(修改時也可以改價格，但設為選填)
    price: Optional[int] = None

class ItemRead(ItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)