# app/models/item.py

from sqlalchemy import Column, Integer, String, Text
from pydantic import BaseModel, ConfigDict
from typing import Optional
# ⚠️ 關鍵：從共用的 base.py 匯入 Base
from app.models.base import Base

# --- 1. 資料庫食譜 (SQLAlchemy) ---
class Item(Base):
    """
    這張表現在叫 'monsters'，用來存怪獸資料。
    """
    __tablename__ = "monsters"

    id = Column(Integer, primary_key=True, index=True)
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
    所有欄位都設為 Optional，方便只更新部分數值
    """
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    attack: Optional[int] = None

class ItemRead(ItemBase):
    id: int
    # Pydantic V2 設定：允許從 ORM 物件讀取資料
    model_config = ConfigDict(from_attributes=True)