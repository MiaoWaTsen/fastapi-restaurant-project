# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.item_service import ItemService
from app.common.deps import get_item_service
# 1. 新增：多匯入一個 ItemCreate
from app.models.item import ItemRead, ItemCreate 

router = APIRouter()

# --- 2. 新增：這就是「新增商品」的櫃檯 (POST) ---
@router.post("/", response_model=ItemRead)
def create_item(
    item_in: ItemCreate, # 服務生手伸出來，跟客人要一張「點菜單」
    service: ItemService = Depends(get_item_service) # 叫主廚來
):
    """
    SOP:
    1. 收到客人的 item_in (點菜單)。
    2. 交給主廚 service.create_item 去做。
    3. 主廚做完會回傳 db_item (包含 ID)。
    4. 把它包裝成 ItemRead 回傳給客人。
    """
    return service.create_item(item_in)
# ----------------------------------------------

@router.get("/", response_model=List[ItemRead])
def read_items(service: ItemService = Depends(get_item_service)):
    items = service.get_all_items()
    return items

@router.get("/{item_id}", response_model=ItemRead)
def read_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    db_item = service.get_item(item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item