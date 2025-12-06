# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import random 

from app.services.item_service import ItemService
from app.common.deps import get_item_service, get_current_user
from app.models.item import ItemRead, ItemCreate, ItemUpdate
from app.models.user import User
from app.common.websocket import manager 

router = APIRouter()

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

@router.put("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    service: ItemService = Depends(get_item_service),
    current_user: User = Depends(get_current_user)
):
    updated_monster = service.update_item(item_id, item_in)
    if updated_monster is None:
        raise HTTPException(status_code=404, detail="Monster not found")
    
    # 如果是攻擊行為 (有傳送 hp 變更)
    if item_in.hp is not None:
        
        # 1. 怪獸反擊！(扣玩家血量)
        # 傷害公式：怪獸攻擊力 + (-5 ~ +5 浮動)
        monster_dmg = max(1, updated_monster.attack + random.randint(-5, 5))
        current_user.hp = max(0, current_user.hp - monster_dmg)
        
        # 廣播戰報 (雙方受傷)
        msg = f"⚔️ 交戰：[{current_user.username}] 對 [{updated_monster.name}] 造成傷害，但也被反擊受了 {monster_dmg} 點傷！"
        await manager.broadcast(msg)

        # 2. 玩家死亡判定
        if current_user.hp <= 0:
            current_user.money = int(current_user.money * 0.8) # 死亡懲罰：掉 20% 錢
            current_user.hp = current_user.max_hp # 免費復活但回城
            await manager.broadcast(f"⚰️ 悲報：勇者 [{current_user.username}] 被野怪打死，噴了 20% 金幣...")

        # 3. 玩家獲得經驗 (沒死才有)
        else:
            exp_gain = 10
            current_user.exp += exp_gain
            if current_user.exp >= 100:
                current_user.level += 1
                current_user.exp = 0 
                current_user.max_hp += 50
                current_user.hp = current_user.max_hp
                current_user.attack += 5
                await manager.broadcast(f"🎉 升級！勇者 [{current_user.username}] 升到了 {current_user.level} 等！")

        # 儲存玩家狀態 (扣血/升級/扣錢)
        service.db.add(current_user)

        # 4. 怪獸死亡與轉生 (保持原本邏輯)
        if updated_monster.hp <= 0:
            gold_drop = random.randint(50, 100)
            current_user.money += gold_drop
            
            await manager.broadcast(f"💀 擊殺：[{updated_monster.name}] 倒下！[{current_user.username}] 獲得 {gold_drop} G！")
            
            new_max_hp = int(updated_monster.max_hp * 1.2)
            new_attack = int(updated_monster.attack * 1.1)
            
            revive_data = ItemUpdate(
                hp=new_max_hp, max_hp=new_max_hp, attack=new_attack,
                description=f"更強的 {updated_monster.name} (Lv Up) 復活了！"
            )
            revived_monster = service.update_item(item_id, revive_data)
            await manager.broadcast(f"⚠️ 警告：[{revived_monster.name}] 轉生復活！")
            
            service.db.commit()
            return revived_monster # 回傳滿血怪獸

        service.db.commit()
    
    return updated_monster

@router.delete("/{item_id}")
def delete_item(item_id: int, service: ItemService = Depends(get_item_service)):
    deleted_item = service.delete_item(item_id)
    if deleted_item is None: raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully", "id": item_id}