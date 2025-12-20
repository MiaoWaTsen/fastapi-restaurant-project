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

# 🔥 資料庫更新：新增大量寶可夢與數據 🔥
POKEDEX_DATA = {
    "妙蛙種子": {"hp": 130, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg"},
    "小火龍": {"hp": 112, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg"},
    "傑尼龜": {"hp": 121, "atk": 121, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg"},
    "妙蛙花": {"hp": 152, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/venusaur.jpg"},
    "噴火龍": {"hp": 130, "atk": 152, "img": "https://img.pokemondb.net/artwork/large/charizard.jpg"},
    "水箭龜": {"hp": 141, "atk": 141, "img": "https://img.pokemondb.net/artwork/large/blastoise.jpg"},
    "毛辮羊": {"hp": 120, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg"},
    "皮卡丘": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"},
    "伊布": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg"},
    "胖丁": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/jigglypuff.jpg"},
    "皮皮": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/clefairy.jpg"},
    "大蔥鴨": {"hp": 120, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg"},
    "呆呆獸": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg"},
    "可達鴨": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg"},
    "卡比獸": {"hp": 175, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/snorlax.jpg"},
    "吉利蛋": {"hp": 220, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/chansey.jpg"},
    "幸福蛋": {"hp": 230, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/blissey.jpg"},
    "拉普拉斯": {"hp": 165, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/lapras.jpg"},
    "快龍":   {"hp": 150, "atk": 148, "img": "https://img.pokemondb.net/artwork/large/dragonite.jpg"},
    "超夢":   {"hp": 150, "atk": 155, "img": "https://img.pokemondb.net/artwork/large/mewtwo.jpg"},
}

# 🔥 初級扭蛋 (1500G) 🔥
GACHA_NORMAL = [
    {"name": "妙蛙種子", "rate": 5}, {"name": "小火龍", "rate": 5}, {"name": "傑尼龜", "rate": 5},
    {"name": "伊布", "rate": 8}, {"name": "皮卡丘", "rate": 8}, {"name": "皮皮", "rate": 10},
    {"name": "胖丁", "rate": 10}, {"name": "毛辮羊", "rate": 8}, {"name": "大蔥鴨", "rate": 12},
    {"name": "呆呆獸", "rate": 12}, {"name": "可達鴨", "rate": 12}, {"name": "卡比獸", "rate": 2},
    {"name": "吉利蛋", "rate": 2}
]

# 🔥 中級扭蛋 (3000G) 🔥
GACHA_MEDIUM = [
    {"name": "妙蛙種子", "rate": 10}, {"name": "小火龍", "rate": 10}, {"name": "傑尼龜", "rate": 10},
    {"name": "伊布", "rate": 10}, {"name": "皮卡丘", "rate": 10}, {"name": "呆呆獸", "rate": 10},
    {"name": "可達鴨", "rate": 10}, {"name": "毛辮羊", "rate": 10}, {"name": "卡比獸", "rate": 5},
    {"name": "吉利蛋", "rate": 3}, {"name": "拉普拉斯", "rate": 3}, {"name": "妙蛙花", "rate": 3},
    {"name": "噴火龍", "rate": 3}, {"name": "水箭龜", "rate": 3}
]

# 🔥 糖果扭蛋 (12 Candy) 🔥
GACHA_CANDY = [
    {"name": "伊布", "rate": 20}, {"name": "皮卡丘", "rate": 20},
    {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10},
    {"name": "卡比獸", "rate": 10}, {"name": "吉利蛋", "rate": 10},
    {"name": "幸福蛋", "rate": 4}, {"name": "拉普拉斯", "rate": 3}, {"name": "快龍", "rate": 3}
]

# 🔥 黃金扭蛋 (3 Golden) 🔥
GACHA_GOLDEN = [
    {"name": "卡比獸", "rate": 30}, {"name": "吉利蛋", "rate": 40},
    {"name": "幸福蛋", "rate": 15}, {"name": "拉普拉斯", "rate": 7},
    {"name": "快龍", "rate": 5}, {"name": "超夢", "rate": 3}
]

ACTIVE_BATTLES = {}

@router.post("/gacha/{gacha_type}")
async def play_gacha(gacha_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inventory = json.loads(current_user.inventory) if current_user.inventory else {}
    
    if gacha_type == 'normal':
        pool = GACHA_NORMAL; cost = 1500
        if current_user.money < cost: raise HTTPException(status_code=400, detail="金幣不足")
        current_user.money -= cost
        msg_type = "初級"
        
    elif gacha_type == 'medium':
        pool = GACHA_MEDIUM; cost = 3000
        if current_user.money < cost: raise HTTPException(status_code=400, detail="金幣不足")
        current_user.money -= cost
        msg_type = "中級"
        
    elif gacha_type == 'candy':
        pool = GACHA_CANDY; cost = 12
        if inventory.get("candy", 0) < cost: raise HTTPException(status_code=400, detail="糖果不足")
        inventory["candy"] -= cost
        msg_type = "糖果"
        
    elif gacha_type == 'golden':
        pool = GACHA_GOLDEN; cost = 3
        if inventory.get("golden_candy", 0) < cost: raise HTTPException(status_code=400, detail="黃金糖果不足")
        inventory["golden_candy"] -= cost
        msg_type = "✨黃金"
        
    else:
        raise HTTPException(status_code=400, detail="未知類型")
    
    current_user.inventory = json.dumps(inventory)

    r = random.randint(1, 100)
    acc = 0
    prize_name = pool[0]["name"]
    for p in pool:
        acc += p["rate"]
        if r <= acc:
            prize_name = p["name"]
            break
            
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
    
    # 廣播稀有獲得
    if gacha_type == 'golden' or prize_name in ['快龍', '超夢', '拉普拉斯', '幸福蛋']:
        await manager.broadcast(f"🎰 恭喜 [{current_user.username}] 在{msg_type}扭蛋中獲得了稀有的 [{prize_name}]！")
        
    return {"message": f"獲得 {prize_name}!", "prize": {"name": prize_name, "img": prize_data["img"]}, "is_new": is_new, "user": current_user}

@router.post("/swap/{target_name}")
async def swap_pokemon(target_name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    storage = json.loads(current_user.pokemon_storage) if current_user.pokemon_storage else {}
    if target_name not in storage:
        if target_name in current_user.unlocked_monsters: storage[target_name] = {"lv": 1, "exp": 0}
        else: raise HTTPException(status_code=400, detail="未解鎖")
    
    base_data = POKEDEX_DATA.get(target_name)
    
    old_name = current_user.pokemon_name
    if old_name in storage:
        storage[old_name]["lv"] = current_user.pet_level
        storage[old_name]["exp"] = current_user.pet_exp
    
    new_stats = storage[target_name]
    current_user.pet_level = new_stats["lv"]
    current_user.pet_exp = new_stats["exp"]
    current_user.pokemon_name = target_name
    current_user.pokemon_image = base_data["img"]
    current_user.pokemon_storage = json.dumps(storage)

    lv = current_user.pet_level
    current_user.max_hp = int(base_data["hp"] * (1.08 ** (lv - 1)))
    current_user.hp = current_user.max_hp
    current_user.attack = int(base_data["atk"] * (1.06 ** (lv - 1)))
    
    db.commit()
    return {"message": f"變身為 {target_name}!", "user": current_user}

@router.post("/heal")
async def buy_heal(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 50: raise HTTPException(status_code=400, detail="金幣不足")
    current_user.money -= 50
    current_user.hp = current_user.max_hp
    db.commit()
    return {"message": "體力已補滿"}

# (PVP 部分保持不變)
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