# app/models/item.py

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel, ConfigDict # Pydantic V2 的語法
from typing import Optional # 舊版 Python 可能需要

# --- 第 1 部分：SQLAlchemy 的基底 (食譜的「設計局」) ---
#
# 我們需要一個「基底」(Base)，
# 未來我們所有的「倉庫食譜」(SQLAlchemy Models) 都要繼承它。
# 這樣 SQLAlchemy 才能統一管理它們。
# (你其他的 model 檔案也可以從這裡 import Base)
Base = declarative_base()


# --- 第 2 部分：SQLAlchemy Model (給「倉庫」看的食譜) ---

class Item(Base):
    """
    這定義了 'Item' (商品) 在「食材倉庫 (DB)」裡
    該長什麼樣子。
    """
    
    # 告訴 SQLAlchemy，這張「桌子(table)」在倉庫裡要叫 "items"
    __tablename__ = "items" 

    # 定義這張桌子有哪些「欄位(column)」
    id = Column(Integer, primary_key=True, index=True) # 商品編號 (主鍵)
    name = Column(String(100), index=True, nullable=False) # 商品名稱 (不允許為空)
    description = Column(Text, nullable=True) # 商品描述 (可選, nullable=True)
    
    # 未來你可以自己加欄位, 例如:
    # price = Column(Float, nullable=False) 


# --- 第 3 部分：Pydantic Schemas (給「客人/服務生」看的菜單) ---
#
# Pydantic 模型 (Schemas) 只負責定義 API 的「資料形狀」，
# 它們**不會**跟資料庫直接溝通。

class ItemBase(BaseModel):
    """
    這是「基礎菜單」(Base Schema)。
    它定義了 Item 最基本的欄位。
    """
    name: str
    description: Optional[str] = None # 允許 description 是空值 (None)

class ItemCreate(ItemBase):
    """
    這是「點餐用 (Create)」的菜單。
    服務生拿這個菜單給客人填 (POST /items/)。
    客人點餐時，只需要提供 name 和 description。
    (id 是由倉庫自動產生的，客人不用填)
    """
    pass # 繼承 ItemBase 的所有欄位，所以不用多寫

class ItemUpdate(ItemBase):
    """
    這是「更新用 (Update)」的菜單 (PUT /items/{id})。
    客人可能只想更新部分資料，所以欄位都設為可選 (Optional)。
    """
    name: Optional[str] = None
    description: Optional[str] = None

class ItemRead(ItemBase):
    """
    這是「送餐用 (Read)」的菜單。
    當服務生把菜端給客人時 (GET /items/)，這道菜應該包含 id。
    """
    id: int
    
    # 這是 Pydantic V2 的關鍵！
    # 告訴 Pydantic：「允許你從 SQLAlchemy 的 Item 物件 (一個 class) 
    # 來讀取資料，並轉換成 Pydantic 的 ItemRead 模型 (一個 dict/JSON)。」
    # 這是「倉庫食譜」和「客人菜單」之間的翻譯機。
    model_config = ConfigDict(from_attributes=True)