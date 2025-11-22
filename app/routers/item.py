# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.item_service import ItemService
from app.common.deps import get_item_service
# 1. 新增：匯入 ItemUpdate
from app.models.item import ItemRead, ItemCreate, ItemUpdate

router = APIRouter()

@router.post("/", response_model=ItemRead)
def create_item(
    item_in: ItemCreate, 
    service: ItemService = Depends(get_item_service)
):
    return service.create_item(item_in)

@router.get("/", response_model=List[ItemRead])
def read_items(service: ItemService = Depends(get_item_service)):
    return service.get_all_items()

@router.get("/{item_id}", response_model=ItemRead)
def read_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    db_item = service.get_item(item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

# --- 2. 新增：修改櫃檯 (PUT) ---
@router.put("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    item_in: ItemUpdate, # 客人會給一張「修改單」
    service: ItemService = Depends(get_item_service)
):
    updated_item = service.update_item(item_id, item_in)
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item

# --- 3. 新增：刪除櫃檯 (DELETE) ---
@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    deleted_item = service.delete_item(item_id)
    if deleted_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # 刪除成功，回傳一個簡單的訊息
    return {"message": "Item deleted successfully", "id": item_id}