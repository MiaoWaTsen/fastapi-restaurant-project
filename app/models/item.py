# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.item_service import ItemService
from app.common.deps import get_item_service, get_current_user # 匯入剛剛寫好的身分驗證
from app.models.item import ItemRead, ItemCreate, ItemUpdate
from app.models.user import User # 匯入玩家模型
from app.common.websocket import manager 

router = APIRouter()

# ... (create_item, read_items, read_item, delete_item 保持不變，為節省篇幅省略) ...
# 請保留原本的 create_item, read_items, read_item, delete_item 程式碼！
# 這裡只貼修改過的 update_item

@router.post("/", response_model=ItemRead)
def create_item(item_in: ItemCreate, service: ItemService = Depends(get_item_service)):
    return service.create_item(item_in)

@router.get("/", response_model=List[ItemRead])
def read_items(service: ItemService = Depends(get_item_service)):
    return service.get_all_items()

@router.get("/{item_id}", response_model=ItemRead)
def read_item(item_id: int, service: ItemService = Depends(get_item_service)):
    db_item = service.get_item(item_id=item_id)
    if db_item is None: raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@router.delete("/{item_id}")
def delete_item(item_id: int, service: ItemService = Depends(get_item_service)):
    deleted_item = service.delete_item(item_id)
    if deleted_item is None: raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully", "id": item_id}


# --- 🔥 修改：攻擊/更新怪獸 (PUT) 🔥 ---
@router.put("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    service: ItemService = Depends(get_item_service),
    # 新增：這裡會強制檢查 Token，並抓出是誰在打
    current_user: User = Depends(get_current_user) 
):
    updated_item = service.update_item(item_id, item_in)
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # 如果有扣血 (代表是攻擊行為)
    if item_in.hp is not None:
        message = f"戰報：勇者 [{current_user.username}] 攻擊了 [{updated_item.name}]！剩餘血量 {updated_item.hp}"
        await manager.broadcast(message)

        # --- 升級系統 ---
        # 每次攻擊獲得 10 經驗
        exp_gain = 10
        current_user.exp += exp_gain
        
        # 簡單的升級公式：每 100 經驗升一級
        if current_user.exp >= 100:
            current_user.level += 1
            current_user.exp = 0 # 歸零或保留餘數看你設計
            current_user.max_hp += 50 # 升級加血上限
            current_user.hp = current_user.max_hp # 升級補滿血
            current_user.attack += 5 # 升級加攻擊
            await manager.broadcast(f"🎉 恭喜！勇者 [{current_user.username}] 升到了 {current_user.level} 等！")

        # 儲存玩家資料
        service.db.add(current_user)
        service.db.commit()
        # ----------------

        # BOSS 轉生邏輯 (保持不變)
        if updated_item.hp == 0:
            await manager.broadcast(f"💀 公告：[{updated_item.name}] 被 [{current_user.username}] 擊敗了！")
            new_max_hp = int(updated_item.max_hp * 1.2)
            new_attack = int(updated_item.attack * 1.1)
            revive_data = ItemUpdate(hp=new_max_hp, max_hp=new_max_hp, attack=new_attack, description=f"更強的 {updated_item.name} 復活了！")
            revived_monster = service.update_item(item_id, revive_data)
            await manager.broadcast(f"⚠️ 警告：[{revived_monster.name}] 轉生復活！")
            return revived_monster
    
    return updated_item