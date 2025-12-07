from sqlalchemy import Column, Integer, String, Boolean
from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.models.base import Base

# --- 資料庫模型 (SQLAlchemy) ---
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=10)
    
    # 用來標記是否為野怪 (雖然後來我們改用動態生成，但保留此欄位以免舊程式碼報錯)
    is_wild = Column(Boolean, default=False) 

# --- 驗證模型 (Pydantic) ---

# 1. 基礎欄位
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    hp: int = 100
    max_hp: int = 100
    attack: int = 10

# 2. 建立時需要的欄位 (這就是報錯說找不到的 ItemCreate)
class ItemCreate(ItemBase):
    pass

# 3. 更新時需要的欄位
class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    attack: Optional[int] = None

# 4. 讀取時回傳的欄位
class ItemRead(ItemBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)