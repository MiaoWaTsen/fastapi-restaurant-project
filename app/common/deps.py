# app/common/deps.py

from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db # 1. 匯入「鑰匙管理員」
from app.services.item_service import ItemService # 2. 匯入「主廚」的職位定義

def get_item_service(
    db: Session = Depends(get_db)
) -> ItemService:
    """
    這就是「標準作業流程 (SOP)」函式。
    
    FastAPI (餐廳經理) 在執行這個SOP時，會：
    
    1. 看到它「依賴 (Depends)」 get_db (鑰匙管理員)。
    2. 立刻跑去呼叫 get_db()，並取得一把乾淨的「倉庫鑰匙 (db)」。
    3. 把這把鑰匙 (db) 當作參數，傳入這個函式 (db: Session = ...)。
    4. 執行函式內的程式碼。
    """
    
    # SOP 的核心步驟：
    # 聘請一位「主廚」(ItemService)，
    # 並在他被聘用時 (建構子 __init__)，
    # 立刻把那把「鑰匙 (db)」塞給他。
    return ItemService(db=db)