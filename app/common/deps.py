# app/common/deps.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.item_service import ItemService

def get_item_service(db: Session = Depends(get_db)) -> ItemService:
    """
    FastAPI 會先呼叫 get_db 取得 db session，
    然後把 db session 傳入 ItemService 的建構子，
    最後把 ItemService 實例回傳。
    """
    return ItemService(db=db)