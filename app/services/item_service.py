# app/services/item_service.py

from sqlalchemy.orm import Session
from app.models import item as item_model 
# 1. 新增：匯入 ItemUpdate
from app.models.item import ItemCreate, ItemUpdate 

class ItemService:
    
    def __init__(self, db: Session):
        self.db = db

    def get_item(self, item_id: int):
        return self.db.query(item_model.Item).filter(item_model.Item.id == item_id).first()

    def get_all_items(self):
        return self.db.query(item_model.Item).all()
    
    def create_item(self, item_in: ItemCreate):
        db_item = item_model.Item(**item_in.model_dump())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    # --- 2. 新增技能：修改訂單 (Update) ---
    def update_item(self, item_id: int, item_in: ItemUpdate):
        # 先把舊的找出來
        db_item = self.get_item(item_id)
        if not db_item:
            return None # 找不到就沒辦法改
        
        # 這裡有個小魔法：exclude_unset=True
        # 意思是：客人沒填寫的欄位，就不要動它 (保留原樣)
        update_data = item_in.model_dump(exclude_unset=True)
        
        # 一個一個欄位更新
        for key, value in update_data.items():
            setattr(db_item, key, value)

        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    # --- 3. 新增技能：取消訂單 (Delete) ---
    def delete_item(self, item_id: int):
        # 先把舊的找出來
        db_item = self.get_item(item_id)
        if not db_item:
            return None # 找不到就沒辦法刪
        
        # 撕掉訂單 (Delete)
        self.db.delete(db_item)
        self.db.commit()
        return db_item