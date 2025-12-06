# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.item_service import ItemService
from app.common.deps import get_item_service
from app.models.item import ItemRead, ItemCreate, ItemUpdate

# --- 關鍵修復：這行就是對講機，絕對不能少！ ---
router = APIRouter()
# ----------------------------------------

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

@router.put("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    item_in: ItemUpdate,
    service: ItemService = Depends(get_item_service)
):
    updated_item = service.update_item(item_id, item_in)
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item

@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    service: ItemService = Depends(get_item_service)
):
    deleted_item = service.delete_item(item_id)
    if deleted_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully", "id": item_id}