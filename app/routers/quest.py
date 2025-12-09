# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
import json

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user

router = APIRouter()

# --- 🌲 野怪資料 (用於生成任務) ---
WILD_DB = [
    {"name": "卡拉卡拉", "base_xp": 20, "base_gold": 45},
    {"name": "喵喵", "base_xp": 30, "base_gold": 55},
    {"name": "皮卡丘", "base_xp": 40, "base_gold": 65},
    {"name": "波波", "base_xp": 50, "base_gold": 75},
    {"name": "海星星", "base_xp": 50, "base_gold": 85}
]

# 🔥 為了避免 Import Error，直接在這裡定義經驗表與升級邏輯 🔥
LEVEL_XP = { 1: 50, 2: 100, 3: 200, 4: 350, 5: 600, 6: 1000, 7: 1800, 8: 3000, 9: 5000, 10: 8000 }

def check_levelup_dual_local(user: User):
    """檢查並執行雙軌升級 (Local版)"""
    msg_list = []
    
    # 1. 訓練師升級
    req_xp_player = LEVEL_XP.get(user.level, 999999)
    if user.exp >= req_xp_player:
        user.level += 1
        user.exp -= req_xp_player
        msg_list.append(f"訓練師升級(Lv.{user.level})")
        
    # 2. 寶可夢升級
    # 限制: 寶可夢等級不能超過訓練師 (除非訓練師也是Lv1)
    if user.pet_level < user.level or (user.level == 1 and user.pet_level == 1):
        req_xp_pet = LEVEL_XP.get(user.pet_level, 999999)
        if user.pet_exp >= req_xp_pet:
            user.pet_level += 1
            user.pet_exp -= req_xp_pet
            
            # 能力成長
            user.max_hp = int(user.max_hp * 1.3)
            user.hp = user.max_hp
            user.attack = int(user.attack * 1.1)
            
            msg_list.append(f"{user.pokemon_name}升級(Lv.{user.pet_level})")
            
    return " & ".join(msg_list) if msg_list else None

# --- API ---

@router.get("/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        quest_list = json.loads(current_user.quests) if current_user.quests else []
    except:
        quest_list = []

    changed = False
    while len(quest_list) < 3:
        # 根據玩家等級解鎖怪物
        unlock_count = min(current_user.level, len(WILD_DB))
        target_idx = random.randint(0, unlock_count - 1)
        target = WILD_DB[target_idx]
        
        count = random.randint(1, 5)
        reward_gold = int(target["base_gold"] * count * 1.5)
        reward_xp = int(target["base_xp"] * count * 1.5)
        
        new_quest = {
            "id": random.randint(1000, 9999),
            "target": target["name"],
            "req": count,
            "now": 0,
            "gold": reward_gold,
            "xp": reward_xp,
            "status": "WAITING"
        }
        quest_list.append(new_quest)
        changed = True
    
    if changed:
        current_user.quests = json.dumps(quest_list)
        db.commit()
        
    return quest_list

@router.post("/accept/{quest_id}")
def accept_quest(quest_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quest_list = json.loads(current_user.quests)
    for q in quest_list:
        if q["id"] == quest_id and q["status"] == "WAITING":
            q["status"] = "ACTIVE"
            current_user.quests = json.dumps(quest_list)
            db.commit()
            return {"message": "已接受任務！"}
    raise HTTPException(status_code=400, detail="任務不存在或狀態錯誤")

@router.post("/claim/{quest_id}")
def claim_quest(quest_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quest_list = json.loads(current_user.quests)
    new_list = []
    claimed = False
    msg = ""
    
    for q in quest_list:
        if q["id"] == quest_id and q["status"] == "COMPLETED":
            # 發獎勵 (雙重經驗)
            current_user.money += q["gold"]
            current_user.exp += q["xp"]     # 訓練師 XP
            current_user.pet_exp += q["xp"] # 寶可夢 XP
            
            msg = f"領取成功！獲得 {q['gold']} G, {q['xp']} XP"
            claimed = True
            
            # 檢查升級
            lvl_msg = check_levelup_dual_local(current_user)
            if lvl_msg:
                msg += f" (🎉 {lvl_msg}！)"
            
            # 移除已完成任務
            continue 
        new_list.append(q)
        
    if not claimed:
        raise HTTPException(status_code=400, detail="無法領取")
        
    current_user.quests = json.dumps(new_list)
    db.commit()
    return {"message": msg, "user": current_user}