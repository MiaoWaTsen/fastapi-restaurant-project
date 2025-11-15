# app/routers/items.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.item_service import ItemService
from app.common.deps import get_item_service # <-- 引入組合好的依賴
# from app.models.schemas import ItemSchema # 假設的 Pydantic Schema

router = APIRouter()

@router.get("/{item_id}") # , response_model=ItemSchema)
def read_item(
    item_id: int,
    # 你的路由函式「聲明」它需要一個 ItemService
    # FastAPI 會自動呼叫 get_item_service 來滿足這個需求
    service: ItemService = Depends(get_item_service)
):
    """
    注意：這個函式現在非常乾淨！
    它不用管 session 怎麼來、service 怎麼建立。
    它只管「使用 service」並回傳結果。
    """
    db_item = service.get_item(item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@router.get("/")
def read_items(
    service: ItemService = Depends(get_item_service)
):
    return service.get_all_items()