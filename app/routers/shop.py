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

# --- 扭蛋機率表 (保持不變) ---
GACHA_NORMAL = [
    {"name": "伊布", "rate": 30, "hp": 260, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg"},
    {"name": "大蔥鴨", "rate": 25, "hp": 220, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg"},
    {"name": "呆呆獸", "rate": 20, "hp": 250, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg"},
    {"name": "可達鴨", "rate": 20, "hp": 250, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg"},
    {"name": "毛辮羊", "rate": 5, "hp": 300, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg"},
]

GACHA_RARE = [
    {"name": "伊布", "rate": 20, "hp": 260, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg"},
    {"name": "大蔥鴨", "rate": 20, "hp": 220, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg"},
    {"name": "呆呆獸", "rate": 15, "hp": 250, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg"},
    {"name": "可達鴨", "rate": 15, "hp": 250, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg"},
    {"name": "毛辮羊", "rate": 10, "hp": 300, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg"},
    {"name": "拉普拉斯", "rate": 4, "hp": 320, "img": "https://img.pokemondb.net/artwork/large/lapras.jpg"},
    {"name": "吉利蛋", "rate": 3, "hp": 350, "img": "https://img.pokemondb.net/artwork/large/chansey.jpg"},
    {"name": "幸福蛋", "rate": 3, "hp": 380, "img": "https://img.pokemondb.net/artwork/large/blissey.jpg"},
]

# Key: tuple(id1, id2) -> Value: { "turn": current_player_id }
ACTIVE_BATTLES = {}

@router.post("/gacha/{gacha_type}")
async def play_gacha(gacha_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pool = GACHA_NORMAL if gacha_type == 'normal' else GACHA_RARE
    cost = 2000 if gacha_type == 'normal' else 5000
    if current_user.money < cost: raise HTTPException(status_code=400, detail=f"金幣不足！需要 {cost} G")
    current_user.money -= cost
    r = random.randint(1, 100)
    acc = 0
    prize = pool[0]
    for p in pool:
        acc += p["rate"]
        if r <= acc:
            prize = p
            break
    current_user.pokemon_name = prize["name"]
    current_user.pokemon_image = prize["img"]
    current_user.max_hp = prize["hp"]
    current_user.hp = prize["hp"]
    current_user.attack = int(prize["hp"] * 0.15)
    db.commit()
    await manager.broadcast(f"🎰 恭喜！勇者 [{current_user.username}] 透過{gacha_type}扭蛋獲得了 [{prize['name']}]！")
    return {"message": f"獲得了 {prize['name']}！", "user": current_user}

@router.post("/heal")
async def buy_heal(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 50: raise HTTPException(status_code=400, detail="金幣不足")
    current_user.money -= 50
    current_user.hp = current_user.max_hp
    db.commit()
    return {"message": "體力已補滿"}

# --- PVP 系統 (邀請制) ---

# 1. 發送邀請
@router.post("/duel/invite/{target_id}")
async def invite_duel(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == target_id).first()
    if not target: raise HTTPException(status_code=404, detail="找不到對手")
    
    # 廣播邀請：DUEL_INVITE|發起者ID|發起者名|受邀者ID|受邀者名
    msg = f"EVENT:DUEL_INVITE|{current_user.id}|{current_user.username}|{target.id}|{target.username}"
    await manager.broadcast(msg)
    return {"message": "邀請已發送"}

# 2. 接受邀請 (開始戰鬥)
@router.post("/duel/accept/{target_id}")
async def accept_duel(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == target_id).first()
    if not target: raise HTTPException(status_code=404, detail="找不到對手")

    # 初始化戰鬥狀態 (小ID在前作為key)
    battle_key = tuple(sorted((current_user.id, target.id)))
    # 設定：接受者先攻 (或發起者先攻，這裡設為 target(發起者) 先攻)
    ACTIVE_BATTLES[battle_key] = {"turn": target.id}
    
    # 廣播開始：DUEL_START|發起者ID(先攻)|發起者名|接受者ID|接受者名
    msg = f"EVENT:DUEL_START|{target.id}|{target.username}|{current_user.id}|{current_user.username}"
    await manager.broadcast(msg)
    return {"message": "決鬥開始"}

# 3. 拒絕邀請
@router.post("/duel/reject/{target_id}")
async def reject_duel(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == target_id).first()
    # 廣播拒絕：DUEL_REJECT|拒絕者ID|拒絕者名|被拒者ID
    msg = f"EVENT:DUEL_REJECT|{current_user.id}|{current_user.username}|{target.id}"
    await manager.broadcast(msg)
    return {"message": "已拒絕"}

# 4. 執行攻擊
@router.post("/pvp/{target_id}")
async def pvp_attack(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == target_id).first()
    if not target: raise HTTPException(status_code=404, detail="找不到對手")
    
    battle_key = tuple(sorted((current_user.id, target_id)))
    if battle_key not in ACTIVE_BATTLES:
        ACTIVE_BATTLES[battle_key] = {"turn": current_user.id} # 容錯
        
    battle = ACTIVE_BATTLES[battle_key]
    
    # 回合檢查
    if battle["turn"] != current_user.id:
        raise HTTPException(status_code=400, detail="還沒輪到你！")
    
    # 交換回合
    battle["turn"] = target_id
    
    # 計算傷害 (簡單模擬，實際應由前端傳 move 資訊更佳，這裡配合前端架構簡化)
    # 前端透過 WebSocket 更新血量，這裡只負責廣播「換人」訊號
    # 但為了防止作弊，我們應該在這裡廣播「攻擊發生了」
    
    # 廣播攻擊事件：EVENT:PVP_MOVE|攻擊者ID|受害者ID
    msg = f"EVENT:PVP_MOVE|{current_user.id}|{target.id}"
    await manager.broadcast(msg)
    
    return {"message": "攻擊成功"}

# 5. 戰鬥結束 (清理狀態)
@router.post("/duel/end/{target_id}")
async def end_duel_api(target_id: int, current_user: User = Depends(get_current_user)):
    battle_key = tuple(sorted((current_user.id, target_id)))
    if battle_key in ACTIVE_BATTLES:
        del ACTIVE_BATTLES[battle_key]
    return {"message": "戰鬥結束"}