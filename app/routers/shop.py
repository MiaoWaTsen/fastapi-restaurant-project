# app/routers/shop.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Tuple
import random
import json

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.common.websocket import manager 

router = APIRouter()

# 數值庫 (保持不變)
POKEDEX_DATA = {
    "妙蛙種子": {"hp": 220, "atk": 105, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg"},
    "小火龍": {"hp": 180, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg"},
    "傑尼龜": {"hp": 200, "atk": 110, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg"},
    "伊布": {"hp": 260, "atk": 115, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg"},
    "大蔥鴨": {"hp": 220, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg"},
    "呆呆獸": {"hp": 300, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg"},
    "可達鴨": {"hp": 250, "atk": 100, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg"},
    "毛辮羊": {"hp": 320, "atk": 85, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg"},
    "拉普拉斯": {"hp": 350, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/lapras.jpg"},
    "吉利蛋": {"hp": 450, "atk": 60, "img": "https://img.pokemondb.net/artwork/large/chansey.jpg"},
    "幸福蛋": {"hp": 500, "atk": 70, "img": "https://img.pokemondb.net/artwork/large/blissey.jpg"},
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

@router.post("/gacha/{gacha_type}")
async def play_gacha(gacha_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pool = GACHA_NORMAL if gacha_type == 'normal' else GACHA_RARE
    cost = 2000 if gacha_type == 'normal' else 5000
    if current_user.money < cost: raise HTTPException(status_code=400, detail=f"金幣不足！")
    
    current_user.money -= cost
    r = random.randint(1, 100)
    acc = 0
    prize_name = pool[0]["name"]
    for p in pool:
        acc += p["rate"]
        if r <= acc:
            prize_name = p["name"]
            break
            
    # 更新解鎖 & 初始化倉庫數據
    storage = json.loads(current_user.pokemon_storage) if current_user.pokemon_storage else {}
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    
    is_new = False
    if prize_name not in unlocked:
        unlocked.append(prize_name)
        current_user.unlocked_monsters = ",".join(unlocked)
        # 初始化這隻新寶可夢的等級
        storage[prize_name] = {"lv": 1, "exp": 0}
        current_user.pokemon_storage = json.dumps(storage)
        is_new = True
    
    db.commit()
    prize_data = POKEDEX_DATA.get(prize_name, {"img": ""})
    
    return {"message": f"獲得了 {prize_name}！", "prize": {"name": prize_name, "img": prize_data["img"]}, "is_new": is_new, "user": current_user}

@router.post("/swap/{target_name}")
async def swap_pokemon(target_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. 檢查解鎖
    storage = json.loads(current_user.pokemon_storage)
    if target_name not in storage:
        # 容錯：如果有解鎖但沒在 storage 裡，初始化它
        if target_name in current_user.unlocked_monsters:
            storage[target_name] = {"lv": 1, "exp": 0}
        else:
            raise HTTPException(status_code=400, detail="尚未解鎖此寶可夢")
    
    base_data = POKEDEX_DATA.get(target_name)
    if not base_data: raise HTTPException(status_code=400, detail="資料錯誤")

    # 2. 🔥 存檔舊角色狀態 🔥
    old_name = current_user.pokemon_name
    if old_name in storage:
        storage[old_name]["lv"] = current_user.pet_level
        storage[old_name]["exp"] = current_user.pet_exp
    
    # 3. 🔥 讀取新角色狀態 🔥
    new_stats = storage[target_name]
    current_user.pet_level = new_stats["lv"]
    current_user.pet_exp = new_stats["exp"]
    current_user.pokemon_name = target_name
    current_user.pokemon_image = base_data["img"]
    
    # 4. 更新倉庫數據 (保存)
    current_user.pokemon_storage = json.dumps(storage)

    # 5. 重新計算能力值 (根據 pet_level)
    level = current_user.pet_level
    current_user.max_hp = int(base_data["hp"] * (1.3 ** (level - 1)))
    current_user.hp = current_user.max_hp
    current_user.attack = int(base_data["atk"] * (1.1 ** (level - 1)))
    
    db.commit()
    return {"message": f"變身為 {target_name} (Lv.{level})！", "user": current_user}

# ... (heal, pvp related APIs unchanged)
@router.post("/heal")
async def buy_heal(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 50: raise HTTPException(status_code=400, detail="金幣不足")
    current_user.money -= 50
    current_user.hp = current_user.max_hp
    db.commit()
    return {"message": "體力已補滿"}

@router.post("/duel/invite/{target_id}")
async def invite_duel(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == target_id).first()
    if not target: raise HTTPException(status_code=404, detail="找不到對手")
    msg = f"EVENT:DUEL_INVITE|{current_user.id}|{current_user.username}|{target.id}|{target.username}"
    await manager.broadcast(msg)
    return {"message": "邀請已發送"}

@router.post("/duel/accept/{target_id}")
async def accept_duel(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == target_id).first()
    if not target: raise HTTPException(status_code=404, detail="找不到對手")
    battle_key = tuple(sorted((current_user.id, target.id)))
    ACTIVE_BATTLES[battle_key] = {"turn": target.id}
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