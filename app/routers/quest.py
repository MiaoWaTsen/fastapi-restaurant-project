# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
import json

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user
from app.routers.auth import check_levelup

router = APIRouter()

# 🌲 野怪資料 (需與 item.py 同步，用於生成任務)
WILD_DB = [
    {"name": "卡拉卡拉", "base_xp": 20, "base_gold": 45}, # Index 0 (Lv1)
    {"name": "喵喵", "base_xp": 30, "base_gold": 55},     # Index 1 (Lv2)
    {"name": "皮卡丘", "base_xp": 40, "base_gold": 65},   # Index 2 (Lv3)
    {"name": "波波", "base_xp": 50, "base_gold": 75},     # Index 3 (Lv4)
    {"name": "海星星", "base_xp": 50, "base_gold": 85}    # Index 4 (Lv5)
]

@router.get("/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 讀取現有任務
    try:
        quest_list = json.loads(current_user.quests) if current_user.quests else []
    except:
        quest_list = []

    # 如果任務少於 3 個，補滿
    changed = False
    while len(quest_list) < 3:
        # 1. 決定能遭遇的怪 (Index < level)
        unlock_count = min(current_user.level, len(WILD_DB))
        target_idx = random.randint(0, unlock_count - 1)
        target = WILD_DB[target_idx]
        
        # 2. 隨機數量 (1~5隻)
        count = random.randint(1, 5)
        
        # 3. 計算獎勵 (基礎獎勵 * 數量 * 1.5倍獎勵係數)
        reward_gold = int(target["base_gold"] * count * 1.5)
        reward_xp = int(target["base_xp"] * count * 1.5)
        
        new_quest = {
            "id": random.randint(1000, 9999), # 隨機ID
            "target": target["name"],
            "req": count,
            "now": 0,
            "gold": reward_gold,
            "xp": reward_xp,
            "status": "WAITING" # WAITING (未接), ACTIVE (進行中), COMPLETED (可領獎)
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
            # 發獎勵
            current_user.money += q["gold"]
            current_user.exp += q["xp"]
            msg = f"領取成功！獲得 {q['gold']} G, {q['xp']} XP"
            claimed = True
            
            # 檢查升級
            if check_levelup(current_user):
                msg += f" (🎉 升級！)"
            
            # 任務完成後從列表中移除 (這樣下次 get 就會補新的)
            continue 
        new_list.append(q)
        
    if not claimed:
        raise HTTPException(status_code=400, detail="無法領取")
        
    current_user.quests = json.dumps(new_list)
    db.commit()
    return {"message": msg, "user": current_user}