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

# 🔥 寶可夢數據庫 (PDF Source 160) 🔥
POKEDEX_DATA = {
    "妙蛙種子": {"hp": 130, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg"},
    "小火龍": {"hp": 112, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg"},
    "傑尼龜": {"hp": 121, "atk": 121, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg"},
    "皮卡丘": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"},
    "伊布": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg"},
    "大蔥鴨": {"hp": 120, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg"},
    "呆呆獸": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg"},
    "可達鴨": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg"},
    "卡比獸": {"hp": 165, "atk": 100, "img": "https://img.pokemondb.net/artwork/large/snorlax.jpg"},
    "吉利蛋": {"hp": 180, "atk": 80, "img": "https://img.pokemondb.net/artwork/large/chansey.jpg"},
    "幸福蛋": {"hp": 185, "atk": 85, "img": "https://img.pokemondb.net/artwork/large/blissey.jpg"},
    "快龍":   {"hp": 150, "atk": 148, "img": "https://img.pokemondb.net/artwork/large/dragonite.jpg"}, # PDF 幸福蛋重複，推測最後一隻是快龍或更強的
}

# 初級扭蛋 (2000G)
GACHA_NORMAL = [
    {"name": "伊布", "rate": 10}, {"name": "皮卡丘", "rate": 10},
    {"name": "大蔥鴨", "rate": 20}, {"name": "呆呆獸", "rate": 20}, {"name": "可達鴨", "rate": 20},
    {"name": "卡比獸", "rate": 8}, {"name": "吉利蛋", "rate": 6}, {"name": "幸福蛋", "rate": 4},
    {"name": "快龍", "rate": 2}
]

# 糖果扭蛋 (10G)
GACHA_CANDY = [
    {"name": "伊布", "rate": 35}, {"name": "皮卡丘", "rate": 35},
    {"name": "卡比獸", "rate": 10}, {"name": "吉利蛋", "rate": 10},
    {"name": "幸福蛋", "rate": 7}, {"name": "快龍", "rate": 3}
]

ACTIVE_BATTLES = {}

@router.post("/gacha/{gacha_type}")
async def play_gacha(gacha_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 決定池與價格
    if gacha_type == 'normal':
        pool = GACHA_NORMAL; cost = 2000; currency = "money"
    elif gacha_type == 'candy':
        pool = GACHA_CANDY; cost = 10; currency = "candy"
    else:
        raise HTTPException(status_code=400, detail="未知扭蛋類型")
    
    # 扣款檢查
    inventory = json.loads(current_user.inventory) if current_user.inventory else {}
    if currency == "money":
        if current_user.money < cost: raise HTTPException(status_code=400, detail="金幣不足")
        current_user.money -= cost
    else:
        if inventory.get("candy", 0) < cost: raise HTTPException(status_code=400, detail="糖果不足")
        inventory["candy"] -= cost
        current_user.inventory = json.dumps(inventory)

    # 抽獎
    r = random.randint(1, 100)
    acc = 0
    prize_name = pool[0]["name"]
    for p in pool:
        acc += p["rate"]
        if r <= acc:
            prize_name = p["name"]
            break
            
    # 解鎖
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    storage = json.loads(current_user.pokemon_storage) if current_user.pokemon_storage else {}
    is_new = False
    
    if prize_name not in unlocked:
        unlocked.append(prize_name)
        current_user.unlocked_monsters = ",".join(unlocked)
        storage[prize_name] = {"lv": 1, "exp": 0}
        current_user.pokemon_storage = json.dumps(storage)
        is_new = True
    
    db.commit()
    prize_data = POKEDEX_DATA.get(prize_name, {"img": ""})
    
    msg_type = "糖果" if gacha_type == 'candy' else "初級"
    await manager.broadcast(f"🎰 [{current_user.username}] 透過{msg_type}扭蛋獲得了 [{prize_name}]！")
    
    return {"message": f"獲得 {prize_name}!", "prize": {"name": prize_name, "img": prize_data["img"]}, "is_new": is_new, "user": current_user}

@router.post("/swap/{target_name}")
async def swap_pokemon(target_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    storage = json.loads(current_user.pokemon_storage)
    if target_name not in storage:
        if target_name in current_user.unlocked_monsters: storage[target_name] = {"lv": 1, "exp": 0}
        else: raise HTTPException(status_code=400, detail="未解鎖")
    
    base_data = POKEDEX_DATA.get(target_name)
    
    # 存檔舊角
    old_name = current_user.pokemon_name
    if old_name in storage:
        storage[old_name]["lv"] = current_user.pet_level
        storage[old_name]["exp"] = current_user.pet_exp
    
    # 讀取新角
    new_stats = storage[target_name]
    current_user.pet_level = new_stats["lv"]
    current_user.pet_exp = new_stats["exp"]
    current_user.pokemon_name = target_name
    current_user.pokemon_image = base_data["img"]
    current_user.pokemon_storage = json.dumps(storage)

    # 數值計算
    # HP*1.06^(lv-1), ATK*1.12^(lv-1)
    lv = current_user.pet_level
    current_user.max_hp = int(base_data["hp"] * (1.06 ** (lv - 1)))
    current_user.hp = current_user.max_hp
    current_user.attack = int(base_data["atk"] * (1.12 ** (lv - 1)))
    
    db.commit()
    return {"message": f"變身為 {target_name}!", "user": current_user}

# ... (heal, pvp related APIs 保持不變，篇幅省略，請保留原有的 invite/accept/attack/end) ...
# 請務必保留原有的 invite_duel, accept_duel, reject_duel, pvp_attack, end_duel_api
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
    # 等級低者先攻
    first = target.id if target.level <= current_user.level else current_user.id
    battle_key = tuple(sorted((current_user.id, target.id)))
    ACTIVE_BATTLES[battle_key] = {"turn": first}
    msg = f"EVENT:DUEL_START|{target.id}|{target.username}|{current_user.id}|{current_user.username}|{first}"
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