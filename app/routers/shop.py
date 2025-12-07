from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
import random

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.common.websocket import manager 

router = APIRouter()

# --- 扭蛋機率表 (PDF Source 75-100, 101-121) ---

# 初級扭蛋 (2000G)
GACHA_NORMAL = [
    {"name": "伊布", "rate": 30, "hp": 260, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg"},
    {"name": "大蔥鴨", "rate": 25, "hp": 220, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg"},
    {"name": "呆呆獸", "rate": 20, "hp": 250, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg"},
    {"name": "可達鴨", "rate": 20, "hp": 250, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg"},
    {"name": "毛辮羊", "rate": 5, "hp": 300, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg"},
]

# 中級扭蛋 (5000G)
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

# --- PVP 狀態管理 (記憶體) ---
# Key: tuple(id1, id2) (id小在前) -> Value: { "turn": current_player_id }
ACTIVE_BATTLES = {}

@router.post("/gacha/{gacha_type}")
async def play_gacha(
    gacha_type: str, # 'normal' or 'rare'
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pool = GACHA_NORMAL if gacha_type == 'normal' else GACHA_RARE
    cost = 2000 if gacha_type == 'normal' else 5000 # [cite: 75, 101]
    
    if current_user.money < cost:
        raise HTTPException(status_code=400, detail=f"金幣不足！需要 {cost} G")
    
    current_user.money -= cost
    
    # 根據機率權重抽獎
    r = random.randint(1, 100)
    acc = 0
    prize = pool[0] # 預設
    for p in pool:
        acc += p["rate"]
        if r <= acc:
            prize = p
            break
            
    # 更新玩家寶可夢 (數值繼承等級加成邏輯暫時簡化為直接替換基礎值，或你需要保留等級加成？)
    # 這裡我們直接替換成新寶可夢的基礎數值，因為 PDF 給定的是基礎血量
    current_user.pokemon_name = prize["name"]
    current_user.pokemon_image = prize["img"]
    current_user.max_hp = prize["hp"]
    current_user.hp = prize["hp"] # 補滿血
    
    # 攻擊力 PDF 沒有明寫扭蛋怪的基礎攻擊，這裡給一個與血量成正比的估算值
    current_user.attack = int(prize["hp"] * 0.15) 
    
    db.commit()
    
    msg = f"🎰 恭喜！勇者 [{current_user.username}] 透過{gacha_type}扭蛋獲得了 [{prize['name']}]！"
    await manager.broadcast(msg)
    
    return {"message": f"獲得了 {prize['name']}！", "user": current_user}

@router.post("/heal")
async def buy_heal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cost = 50
    if current_user.money < cost:
        raise HTTPException(status_code=400, detail="金幣不足")
    
    current_user.money -= cost
    current_user.hp = current_user.max_hp
    db.commit()
    return {"message": "體力已補滿"}

# --- PVP 系統 (含回合鎖) ---

@router.post("/duel/start/{target_id}")
async def start_duel_api(
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target = db.query(User).filter(User.id == target_id).first()
    if not target: raise HTTPException(status_code=404, detail="找不到對手")
    
    # 初始化戰鬥狀態
    # 確保 key 順序一致 (小 ID 在前)，這樣 A打B 和 B打A 會對應到同一個戰鬥
    battle_key = tuple(sorted((current_user.id, target.id)))
    
    # 設定：發起者先攻
    ACTIVE_BATTLES[battle_key] = {"turn": current_user.id}
    
    # 廣播訊號
    msg = f"EVENT:DUEL_START|{current_user.id}|{current_user.username}|{target.id}|{target.username}"
    await manager.broadcast(msg)
    
    return {"message": "決鬥開始"}

@router.post("/pvp/{target_id}")
async def pvp_attack(
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. 驗證對手
    target = db.query(User).filter(User.id == target_id).first()
    if not target: raise HTTPException(status_code=404, detail="找不到對手")
    
    # 2. 驗證回合 (防止手速作弊)
    battle_key = tuple(sorted((current_user.id, target_id)))
    
    # 如果戰鬥不存在 (可能伺服器重啟過)，重新初始化
    if battle_key not in ACTIVE_BATTLES:
        ACTIVE_BATTLES[battle_key] = {"turn": current_user.id}
        
    battle = ACTIVE_BATTLES[battle_key]
    
    # 🔥 關鍵檢查：是不是你的回合？ 🔥
    if battle["turn"] != current_user.id:
        raise HTTPException(status_code=400, detail="還沒輪到你！請等待對手行動。")
    
    # 3. 執行傷害 (這裡簡單計算，實際數值由前端傳來可能不安全，建議後端重算，但為了配合前端目前的設計，我們這裡做簡單扣血)
    # 為了安全性，最好是在後端計算傷害。這裡模擬一下：
    damage = int(current_user.attack * 1.0) # 基礎傷害
    target.hp = max(0, target.hp - damage)
    
    # 4. 交換回合
    battle["turn"] = target_id
    
    # 5. 結算
    msg = f"⚔️ PVP: [{current_user.username}] 攻擊了 [{target.username}]！"
    
    if target.hp <= 0:
        win_money = int(target.money * 0.1)
        target.money -= win_money
        current_user.money += win_money
        msg = f"🏆 勝利！[{current_user.username}] 擊敗了 [{target.username}] 並搶走了 {win_money} G！"
        # 戰鬥結束，移除狀態
        if battle_key in ACTIVE_BATTLES:
            del ACTIVE_BATTLES[battle_key]
    
    db.commit()
    await manager.broadcast(msg)
    
    return {"message": "攻擊成功", "turn_swapped": True}