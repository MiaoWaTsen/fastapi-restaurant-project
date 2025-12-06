# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import random # 引入隨機模組，用來計算金幣掉落

from app.services.item_service import ItemService
from app.common.deps import get_item_service, get_current_user
from app.models.item import ItemRead, ItemCreate, ItemUpdate
from app.models.user import User
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

# --- 攻擊/更新怪獸 (PUT) - 核心邏輯區 ---
@router.put("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    service: ItemService = Depends(get_item_service),
    current_user: User = Depends(get_current_user) # 必須登入才能攻擊
):
    # 1. 執行本次攻擊/更新
    updated_monster = service.update_item(item_id, item_in)
    if updated_monster is None:
        raise HTTPException(status_code=404, detail="Monster not found")
    
    # 2. 如果這次操作涉及血量變化 (代表是攻擊或補血)
    if item_in.hp is not None:
        
        # A. 廣播受傷戰報
        message = f"戰報：勇者 [{current_user.username}] 攻擊了 [{updated_monster.name}]！剩餘血量 {updated_monster.hp}"
        await manager.broadcast(message)

        # B. 獲得經驗值機制
        # 只要有攻擊（不管有沒有打死），就加經驗
        exp_gain = 10
        current_user.exp += exp_gain
        
        # 檢查升級 (每 100 經驗升一級)
        if current_user.exp >= 100:
            current_user.level += 1
            current_user.exp = 0 
            current_user.max_hp += 50
            current_user.hp = current_user.max_hp
            current_user.attack += 5
            await manager.broadcast(f"🎉 恭喜！勇者 [{current_user.username}] 升到了 {current_user.level} 等！")

        # 先暫存玩家狀態 (還沒 Commit，因為下面可能還有金幣要拿)
        service.db.add(current_user)

        # 🔥 C. 死亡判定與轉生機制 (含金幣掉落) 🔥
        if updated_monster.hp <= 0:
            
            # 💰 1. 掉落金幣邏輯
            # 隨機獲得 50 ~ 100 金幣
            gold_drop = random.randint(50, 100)
            current_user.money += gold_drop
            
            # 廣播擊殺與獎勵
            await manager.broadcast(f"💀 公告：[{updated_monster.name}] 被 [{current_user.username}] 擊敗了！獲得 {gold_drop} 金幣！(目前持有: {current_user.money})")
            
            # 🛠️ 2. 轉生變強邏輯
            # 血量變 1.2 倍，攻擊變 1.1 倍
            new_max_hp = int(updated_monster.max_hp * 1.2)
            new_attack = int(updated_monster.attack * 1.1)
            
            # 準備復活數據
            revive_data = ItemUpdate(
                hp=new_max_hp, 
                max_hp=new_max_hp, 
                attack=new_attack,
                description=f"更強的 {updated_monster.name} (Lv Up) 復活了！"
            )
            
            # 執行復活更新
            revived_monster = service.update_item(item_id, revive_data)
            
            # 廣播復活訊息
            await manager.broadcast(f"⚠️ 警告：[{revived_monster.name}] 轉生復活！HP 上限提升至 {revived_monster.max_hp}！")
            
            # 💾 儲存所有變更 (包含玩家的金幣、經驗、怪獸的復活)
            service.db.commit()
            
            # 🔙 重要：回傳「復活後」的怪獸給前端
            # 這樣前端畫面會瞬間回滿血，而不是卡在 0 血
            return revived_monster

        # 如果沒死，就儲存玩家經驗值就好
        service.db.commit()
    
    return updated_monster

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