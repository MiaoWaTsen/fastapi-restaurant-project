# app/routers/shop.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Tuple
import random

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.common.websocket import manager 

router = APIRouter()

# --- 寶可夢基礎數值資料庫 (用於換角計算) ---
# 包含所有扭蛋 + 御三家
POKEDEX_DATA = {
    "妙蛙種子": {"hp": 200, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg"},
    "小火龍": {"hp": 160, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg"},
    "傑尼龜": {"hp": 180, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg"},
    "伊布": {"hp": 260, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg"},
    "大蔥鴨": {"hp": 220, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg"},
    "呆呆獸": {"hp": 250, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg"},
    "可達鴨": {"hp": 250, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg"},
    "毛辮羊": {"hp": 300, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg"},
    "拉普拉斯": {"hp": 320, "img": "https://img.pokemondb.net/artwork/large/lapras.jpg"},
    "吉利蛋": {"hp": 350, "img": "https://img.pokemondb.net/artwork/large/chansey.jpg"},
    "幸福蛋": {"hp": 380, "img": "https://img.pokemondb.net/artwork/large/blissey.jpg"},
}

GACHA_NORMAL = [
    {"name": "伊布", "rate": 30}, {"name": "大蔥鴨", "rate": 25},
    {"name": "呆呆獸", "rate": 20}, {"name": "可達鴨", "rate": 20}, {"name": "毛辮羊", "rate": 5}
]
GACHA_RARE = [
    {"name": "伊布", "rate": 20}, {"name": "大蔥鴨", "rate": 20}, {"name": "呆呆獸", "rate": 15},
    {"name": "可達鴨", "rate": 15}, {"name": "毛辮羊", "rate": 10}, {"name": "拉普拉斯", "rate": 4},
    {"name": "吉利蛋", "rate": 3}, {"name": "幸福蛋", "rate": 3}
]

ACTIVE_BATTLES = {}

# 1. 扭蛋 (只解鎖，不變身)
@router.post("/gacha/{gacha_type}")
async def play_gacha(gacha_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pool = GACHA_NORMAL if gacha_type == 'normal' else GACHA_RARE
    cost = 2000 if gacha_type == 'normal' else 5000
    if current_user.money < cost: raise HTTPException(status_code=400, detail=f"金幣不足！需要 {cost} G")
    
    current_user.money -= cost
    r = random.randint(1, 100)
    acc = 0
    prize_name = pool[0]["name"]
    for p in pool:
        acc += p["rate"]
        if r <= acc:
            prize_name = p["name"]
            break
            
    # 更新圖鑑
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    is_new = False
    if prize_name not in unlocked:
        unlocked.append(prize_name)
        current_user.unlocked_monsters = ",".join(unlocked)
        is_new = True
    
    db.commit()
    
    # 回傳抽到的資料給前端，讓玩家選擇是否變身
    prize_data = POKEDEX_DATA.get(prize_name, {"hp": 100, "img": ""})
    return {
        "message": f"獲得了 {prize_name}！", 
        "prize": {"name": prize_name, "img": prize_data["img"]},
        "is_new": is_new,
        "user": current_user
    }

# 2. 換角/變身 API (新功能)
@router.post("/swap/{target_name}")
async def swap_pokemon(target_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 檢查是否已解鎖
    unlocked = current_user.unlocked_monsters.split(',')
    if target_name not in unlocked:
        raise HTTPException(status_code=400, detail="你還沒解鎖這隻寶可夢！")
    
    base_data = POKEDEX_DATA.get(target_name)
    if not base_data: raise HTTPException(status_code=400, detail="資料錯誤")

    # 更新外觀
    current_user.pokemon_name = target_name
    current_user.pokemon_image = base_data["img"]
    
    # 重新計算能力值 (依照等級)
    # 血量成長 1.4倍，攻擊成長 1.2倍
    level = current_user.level
    new_max_hp = int(base_data["hp"] * (1.4 ** (level - 1)))
    new_attack = int((base_data["hp"] * 0.15) * (1.2 ** (level - 1))) # 基礎攻擊約為血量15%
    
    current_user.max_hp = new_max_hp
    current_user.hp = new_max_hp # 換角補滿血
    current_user.attack = new_attack
    
    db.commit()
    return {"message": f"變身為 {target_name}！", "user": current_user}

@router.post("/heal")
async def buy_heal(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 50: raise HTTPException(status_code=400, detail="金幣不足")
    current_user.money -= 50
    current_user.hp = current_user.max_hp
    db.commit()
    return {"message": "體力已補滿"}

# --- PVP ---

@router.post("/duel/invite/{target_id}")
async def invite_duel(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == target_id).first()
    if not target: raise HTTPException(status_code=404, detail="找不到對手")
    msg = f"EVENT:DUEL_INVITE|{current_user.id}|{current_user.username}|{target.id}|{target.username}"
    await manager.broadcast(msg)
    return {"message": "邀請已發送"}

@router.post("/duel/accept/{target_id}")
async def accept_duel(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == target_id).first() # target 是發起者
    if not target: raise HTTPException(status_code=404, detail="找不到對手")

    battle_key = tuple(sorted((current_user.id, target.id)))
    ACTIVE_BATTLES[battle_key] = {"turn": target.id} # 發起者先攻
    
    # 🔥 PVP Bug 修復：確保廣播包含正確的雙方 ID 🔥
    # 格式: EVENT:DUEL_START | 先攻ID | 先攻名 | 後攻ID | 後攻名
    msg = f"EVENT:DUEL_START|{target.id}|{target.username}|{current_user.id}|{current_user.username}"
    await manager.broadcast(msg)
    return {"message": "決鬥開始"}

@router.post("/duel/reject/{target_id}")
async def reject_duel(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    msg = f"EVENT:DUEL_REJECT|{current_user.id}|{current_user.username}|{target_id}"
    await manager.broadcast(msg)
    return {"message": "已拒絕"}

@router.post("/pvp/{target_id}")
async def pvp_attack(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    battle_key = tuple(sorted((current_user.id, target_id)))
    if battle_key not in ACTIVE_BATTLES: ACTIVE_BATTLES[battle_key] = {"turn": current_user.id}
    if ACTIVE_BATTLES[battle_key]["turn"] != current_user.id: raise HTTPException(status_code=400, detail="還沒輪到你！")
    
    ACTIVE_BATTLES[battle_key]["turn"] = target_id
    msg = f"EVENT:PVP_MOVE|{current_user.id}|{target_id}"
    await manager.broadcast(msg)
    return {"message": "攻擊成功"}

@router.post("/duel/end/{target_id}")
async def end_duel_api(target_id: int, current_user: User = Depends(get_current_user)):
    battle_key = tuple(sorted((current_user.id, target_id)))
    if battle_key in ACTIVE_BATTLES: del ACTIVE_BATTLES[battle_key]
    return {"message": "戰鬥結束"}