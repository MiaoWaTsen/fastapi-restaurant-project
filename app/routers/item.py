# app/models/item.py

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel, ConfigDict
from typing import Optional

Base = declarative_base()

# --- 1. 倉庫食譜 (SQLAlchemy Model) ---
class Item(Base):
    """
    對應資料庫中的 'monsters' 表格。
    雖然 Class 叫 Item (為了相容你的舊程式碼)，但它現在代表一隻「怪獸」！
    """
    __tablename__ = "monsters" # 資料表改名，讓系統自動建立一張新表

    id = Column(Integer, primary_key=True, index=True)
    
    # 基本資料
    name = Column(String(100), index=True, nullable=False) # 怪獸名字
    description = Column(Text, nullable=True)              # 介紹
    image_url = Column(String(255), nullable=True)         # 圖片網址
    
    # 戰鬥數值
    hp = Column(Integer, nullable=False, default=100)      # 當前血量
    max_hp = Column(Integer, nullable=False, default=100)  # 最大血量
    attack = Column(Integer, nullable=False, default=10)   # 攻擊力


# --- 2. 菜單 (Pydantic Schemas) ---
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
    """
    所有欄位都設為 Optional，方便我們只扣血 (只更新 hp)
    """
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    attack: Optional[int] = None

class ItemRead(ItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)