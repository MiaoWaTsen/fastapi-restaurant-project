# app/services/item_service.py
from sqlalchemy.orm import Session
from app.models import item as item_model # 假設你的模型在 models/item.py
# from app.models import schemas # 假設你有 Pydantic schemas

class ItemService:
    """
    這個 Service class 依賴 DB Session。
    我們透過建構子 (constructor) 把它傳入。
    """
    def __init__(self, db: Session):
        self.db = db

    def get_item(self, item_id: int):
        return self.db.query(item_model.Item).filter(item_model.Item.id == item_id).first()

    def get_all_items(self):
        return self.db.query(item_model.Item).all()

    # def create_item(self, item: schemas.ItemCreate):
    #     db_item = item_model.Item(**item.dict())
    #     self.db.add(db_item)
    #     self.db.commit()
    #     self.db.refresh(db_item)
    #     return db_item