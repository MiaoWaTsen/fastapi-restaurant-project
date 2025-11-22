# app/services/item_service.py

from sqlalchemy.orm import Session
from app.models import item as item_model # 1. 匯入「倉庫食譜 (SQLAlchemy Model)」

class ItemService:
    """
    這就是「主廚 (Service)」本人。
    它負責所有跟 Item (商品) 相關的「商業邏輯」(動作)。
    """
    
    def __init__(self, db: Session):
        """
        當主廚 (Service) 被「聘用」時，
        SOP (deps.py) 會立刻塞給他一把「倉庫鑰匙 (db Session)」。
        主廚會把它收在口袋裡 (self.db)，等等要用。
        """
        self.db = db

    def get_item(self, item_id: int):
        """
        SOP 1：依據 ID 取得單一商品
        """
        # 主廚拿著鑰匙 (self.db)，
        # 跑去倉庫 (query) 翻「Item 食譜」(item_model.Item)，
        # 並「過濾 (filter)」出 ID 符合的那一項，
        # 最後把「第一筆 (first)」結果拿出來。
        return self.db.query(item_model.Item).filter(item_model.Item.id == item_id).first()

    def get_all_items(self):
        """
        SOP 2：取得所有商品
        """
        # 主廚拿著鑰匙 (self.db)，
        # 跑去倉庫 (query) 翻「Item 食譜」(item_model.Item)，
        # 並把「全部 (all)」都拿出來。
        return self.db.query(item_model.Item).all()
    
    # --- 我們先完成上面兩個 (Read)，等下再來新增 (Create) ---
    
    # def create_item(self, item_schema: ...):
    #     ... (coming soon)