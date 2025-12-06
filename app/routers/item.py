# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.item_service import ItemService
from app.common.deps import get_item_service
from app.models.item import ItemRead, ItemCreate, ItemUpdate
# 1. 匯入廣播站長
from app.common.websocket import manager 

router = APIRouter()

# --- 召喚怪獸 (POST) ---
@router.post("/", response_model=ItemRead)
def create_item(
    item_in: ItemCreate, 
    service: ItemService = Depends(get_item_service)
):
    return service.create_item(item_in)

# --- 讀取所有怪獸 (GET) ---
@router.get("/", response_model=List[ItemRead])
def read_items(service: ItemService = Depends(get_item_service)):
    return service.get_all_items()

# --- 讀取單隻怪獸 (GET) ---
@router.get("/{item_id}", response_model=ItemRead)
def read_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    db_item = service.get_item(item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

# --- 攻擊/更新怪獸 (PUT) - 關鍵修改！ ---
# 注意：這裡改成 async def，因為要用 await 廣播
@router.put("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    service: ItemService = Depends(get_item_service)
):
    updated_item = service.update_item(item_id, item_in)
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # 2. 如果血量有變化，就廣播戰報！
    if item_in.hp is not None:
        message = f"戰報：[{updated_item.name}] 的血量變成了 {updated_item.hp}！"
        await manager.broadcast(message)
    
    return updated_item

# --- 刪除怪獸 (DELETE) ---
@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    deleted_item = service.delete_item(item_id)
    if deleted_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully", "id": item_id}