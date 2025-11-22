# app/services/item_service.py

from sqlalchemy.orm import Session
from app.models import item as item_model 
# 1. 重要！我們要匯入 ItemCreate 才能看懂客人的點菜單
from app.models.item import ItemCreate 

class ItemService:
    """
    這就是「主廚 (Service)」本人。
    它負責所有跟 Item (商品) 相關的「商業邏輯」(動作)。
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_item(self, item_id: int):
        """
        SOP 1：依據 ID 取得單一商品
        """
        return self.db.query(item_model.Item).filter(item_model.Item.id == item_id).first()

    def get_all_items(self):
        """
        SOP 2：取得所有商品
        """
        return self.db.query(item_model.Item).all()
    
    # --- 3. 新增技能：進貨 (Create) ---
    def create_item(self, item_in: ItemCreate):
        """
        主廚收到一張「點菜單 (item_in)」，
        要把上面的資料變成真正的「料理 (SQLAlchemy Model)」，
        然後放進倉庫。
        """
        # 備料：把 Pydantic 格式轉成 SQLAlchemy 格式
        # (**) 是解壓縮語法，把字典填進 Item() 裡面
        db_item = item_model.Item(**item_in.model_dump())
        
        # 入鍋
        self.db.add(db_item)
        
        # 開火 (寫入資料庫)
        self.db.commit()
        
        # 起鍋確認 (拿到自動產生的 ID)
        self.db.refresh(db_item)
        
        return db_item