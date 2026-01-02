# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import random
import json
import uuid

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.routers.shop import POKEDEX_DATA, WILD_UNLOCK_LEVELS 

router = APIRouter()

# 只有一種任務類型：擊敗野怪
QUEST_TYPE = "BATTLE_WILD"

@router.get("/")
def get_daily_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        quests = json.loads(current_user.quests) if current_user.quests else []
    except:
        quests = []
    
    # 隨時保持 3 個任務
    if len(quests) < 3:
        target_level = current_user.pet_level
        if target_level < 1: target_level = 1
        if target_level > 96: target_level = 96 

        valid_species = []
        for lv in range(1, target_level + 1):
            if lv in WILD_UNLOCK_LEVELS:
                valid_species.extend(WILD_UNLOCK_LEVELS[lv])
        
        if not valid_species: valid_species = ["小拉達"]

        while len(quests) < 3:
            target_mon = random.choice(valid_species)
            is_golden = random.random() < 0.05
            
            if is_golden:
                req_count = 5
                reward_desc = "✨ 黃金糖果 x1"
                xp_reward = 0
                gold_reward = 0
            else:
                req_count = random.randint(1, 3)
                
                # 🔥 V2.11.8: 獎勵再下修 (避免通膨)
                # 新公式: XP=Lv*12+30, Gold=Lv*8+50
                base_xp = target_level * 10 + 30
                base_gold = target_level * 6 + 50
                
                multiplier = 1 + (req_count - 1) * 0.2
                
                total_xp = int(base_xp * req_count * multiplier)
                total_gold = int(base_gold * req_count * multiplier)
                
                xp_reward = total_xp
                gold_reward = total_gold
                reward_desc = f"{total_xp} XP & {total_gold} Gold"

            new_q = {
                "id": str(uuid.uuid4()),
                "type": "GOLDEN" if is_golden else QUEST_TYPE,
                "target": target_mon,
                "target_display": f"擊敗 {target_mon} (Lv.{target_level})", 
                "level": target_level, 
                "req": req_count,
                "now": 0,
                "xp": xp_reward,
                "gold": gold_reward,
                "status": "ACTIVE"
            }
            quests.append(new_q)
            
        current_user.quests = json.dumps(quests)
        db.commit()
        
    return quests

@router.post("/abandon/{quest_id}")
def abandon_quest(quest_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        quests = json.loads(current_user.quests)
    except:
        raise HTTPException(status_code=400, detail="任務資料錯誤")
        
    new_quests = [q for q in quests if q["id"] != quest_id]
    
    if len(quests) == len(new_quests):
        raise HTTPException(status_code=404, detail="找不到任務")
        
    if current_user.money < 1000:
        raise HTTPException(status_code=400, detail="金幣不足 1000G")
        
    current_user.money -= 1000
    current_user.quests = json.dumps(new_quests) 
    db.commit()
    return {"message": "已放棄任務 (消耗 1000G)"}

@router.post("/claim/{quest_id}")
def claim_quest(quest_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        quests = json.loads(current_user.quests)
    except:
        quests = []
        
    target_q = next((q for q in quests if q["id"] == quest_id), None)
    if not target_q: raise HTTPException(status_code=404, detail="找不到任務")
    
    if target_q["now"] < target_q["req"]:
        raise HTTPException(status_code=400, detail="任務尚未完成")
        
    msg = ""
    if target_q.get("type") == "GOLDEN":
        try: 
            if not current_user.inventory: inv = {}
            else: inv = json.loads(current_user.inventory)
        except: inv = {}
        inv["golden_candy"] = inv.get("golden_candy", 0) + 1
        current_user.inventory = json.dumps(inv)
        msg = "獲得 ✨ 黃金糖果 x1"
    else:
        xp = target_q.get("xp", 100)
        gold = target_q.get("gold", 100)
        current_user.exp += xp
        current_user.pet_exp += xp
        current_user.money += gold
        msg = f"獲得 {xp} XP & {gold} Gold"
        
    new_quests = [q for q in quests if q["id"] != quest_id]
    current_user.quests = json.dumps(new_quests)
    db.commit()
    
    return {"message": f"任務完成！{msg}"}