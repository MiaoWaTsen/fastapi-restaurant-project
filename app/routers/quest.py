# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
import json
import uuid
import math

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User

# 引用遊戲資料 (解鎖列表)
from app.common.game_data import WILD_UNLOCK_LEVELS

router = APIRouter()

def generate_quest(user_pet_level):
    # 1. 找出玩家當前等級能遇到的所有野怪
    valid_targets = []
    for unlock_lv, mons in WILD_UNLOCK_LEVELS.items():
        if unlock_lv <= user_pet_level:
            valid_targets.extend(mons)
            
    # 若無解鎖 (防呆)，預設小拉達
    if not valid_targets:
        valid_targets = ["小拉達"]
        
    # 2. 隨機選一個目標
    target = random.choice(valid_targets)
    
    # 3. 決定任務類型 (20% 機率是黃金任務)
    is_golden = random.random() < 0.2
    
    if is_golden:
        # 🔥 黃金任務設定：5隻，無經驗錢，只有糖果
        q_type = "GOLDEN"
        req = 5 
        xp = 0
        gold = 0
        desc = f"✨ [黃金] 擊敗 {req} 隻 {target}"
    else:
        # 一般任務設定：1~3隻，有經驗錢
        q_type = "BATTLE_WILD"
        req = random.randint(1, 3)
        desc = f"擊敗 {req} 隻 {target}"

        # 一般任務獎勵公式 (維持 V2.13.11 的曲線)
        base_xp_per_unit = 60 + (user_pet_level * 8)
        base_gold_per_unit = 40 + (user_pet_level * 4)
        
        # 數量加成：req ^ 1.15 (讓 2 隻的獎勵微大於 1 隻的兩倍)
        count_multiplier = req ** 1.15
        
        xp = int(base_xp_per_unit * count_multiplier)
        gold = int(base_gold_per_unit * count_multiplier)
    
    return {
        "id": str(uuid.uuid4()),
        "type": q_type,
        "target": target,
        "target_display": desc,
        "now": 0,
        "req": req,
        "xp": xp,
        "gold": gold,
        "status": "ACTIVE"
    }

@router.get("/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        quests = json.loads(current_user.quests) if current_user.quests else []
    except:
        quests = []
    
    # 🔥 核心邏輯：永遠保持 3 個任務
    changed = False
    while len(quests) < 3:
        new_q = generate_quest(current_user.pet_level)
        quests.append(new_q)
        changed = True
        
    if changed:
        current_user.quests = json.dumps(quests)
        db.commit()
        
    return quests

@router.post("/claim/{quest_id}")
def claim_quest(quest_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        quests = json.loads(current_user.quests)
    except:
        raise HTTPException(status_code=400, detail="任務資料錯誤")
        
    target_q = next((q for q in quests if q["id"] == quest_id), None)
    if not target_q:
        raise HTTPException(status_code=404, detail="找不到此任務")
        
    if target_q["now"] < target_q["req"]:
        raise HTTPException(status_code=400, detail="任務尚未完成")
        
    # 發放獎勵 (XP & Gold，黃金任務這裡會加 0)
    current_user.exp += target_q["xp"]
    current_user.pet_exp += target_q["xp"]
    current_user.money += target_q["gold"]
    
    # 移除已完成任務
    quests = [q for q in quests if q["id"] != quest_id]
    current_user.quests = json.dumps(quests)
    
    msg = ""
    
    # 處理回傳訊息與特殊獎勵
    if target_q["type"] == "GOLDEN":
        try: inv = json.loads(current_user.inventory)
        except: inv = {}
        inv["golden_candy"] = inv.get("golden_candy", 0) + 1
        current_user.inventory = json.dumps(inv)
        msg = "獲得 ✨ 黃金糖果 x1" # 🔥 黃金任務專屬訊息
    else:
        msg = f"獲得 {target_q['xp']} XP, {target_q['gold']} G"

    db.commit()
    return {"message": f"任務完成！{msg}", "user": current_user}

@router.post("/abandon/{quest_id}")
def abandon_quest(quest_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 1000:
        raise HTTPException(status_code=400, detail="金幣不足 1000 G")
        
    try: quests = json.loads(current_user.quests)
    except: quests = []
    
    # 移除任務
    new_quests = [q for q in quests if q["id"] != quest_id]
    
    if len(new_quests) == len(quests):
        raise HTTPException(status_code=404, detail="找不到任務")
        
    current_user.money -= 1000
    current_user.quests = json.dumps(new_quests)
    db.commit()
    
    return {"message": "已放棄任務 (消耗 1000G)"}