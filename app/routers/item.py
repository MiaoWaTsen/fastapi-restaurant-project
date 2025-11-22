# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List # 用來標註「清單」類型

from app.services.item_service import ItemService # 1. (選擇性) 匯入主廚的「類型」
from app.common.deps import get_item_service # 2. 匯入「SOP 手冊」
from app.models.item import ItemRead # 3. 匯入「送餐用菜單 (Pydantic Schema)」

# 建立這個服務生團隊 (Router)
router = APIRouter()

@router.get("/", response_model=List[ItemRead])
def read_items(
    # --- 關鍵的依賴注入 ---
    # 服務生 (函式) 聲明：「我需要一位主廚！」
    # FastAPI (經理) 會立刻去執行 get_item_service (SOP)
    # 並把「配備好鑰匙的主廚」當作 service 變數傳進來。
    service: ItemService = Depends(get_item_service)
):
    """
    SOP for 服務生:
    1. 叫主廚來。 (FastAPI 幫你做了)
    2. 把「取得所有商品」這個指令傳達給主廚。
    3. 主廚會把「所有商品 (items)」拿回來。
    4. 把商品回傳給客人。
    
    (response_model=List[ItemRead] 會自動幫你把資料
     從「倉庫食譜」翻譯成「客人菜單」)
    """
    items = service.get_all_items()
    return items

@router.get("/{item_id}", response_model=ItemRead)
def read_item(
    item_id: int, # 服務生從 URL 取得客人要的「商品編號」
    service: ItemService = Depends(get_item_service) # 再次呼叫 SOP 找到主廚
):
    """
    SOP for 服務生:
    1. 叫主廚來。
    2. 把「取得 ID 為 {item_id} 的商品」這個指令傳達給主廚。
    3. 主廚會把「那件商品 (db_item)」拿回來。
    4. (重要) 檢查主廚是不是兩手空空 (None)？
    5. 如果是，立刻跟客人說 404 找不到。
    6. 如果有找到，把商品回傳給客人。
    """
    db_item = service.get_item(item_id=item_id)
    if db_item is None:
        # 如果主廚找不到商品 (回傳 None)，
        # 服務生要負責回報 404 錯誤。
        raise HTTPException(status_code=404, detail="Item not found")
    
    return db_item