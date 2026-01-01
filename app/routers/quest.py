# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import random
import json
import uuid

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.routers.shop import POKEDEX_DATA

router = APIRouter()

QUEST_TYPES = ["BATTLE_WILD", "COLLECT_MON"]

@router.get("/")
def get_daily_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        quests = json.loads(current_user.quests) if current_user.quests else []
    except:
        quests = []
    
    # 如果沒有任務，生成 3 個
    if len(quests) == 0:
        for _ in range(3):
            q_type = random.choice(QUEST_TYPES)
            target = random.choice(list(POKEDEX_DATA.keys()))
            req = random.randint(3, 8)
            
            # 🔥 動態獎勵公式：確保比打野怪好賺 (V2.10.5)
            # 野怪公式: (Base/20)*Lv + 30
            # 任務公式: (XP ~ Lv*30), (Gold ~ Lv*40) -> 相當於打 5~10 隻怪
            reward_xp = current_user.level * 30 + 150
            reward_gold = current_user.level * 40 + 200
            
            is_golden = random.random() < 0.05
            
            new_q = {
                "id": str(uuid.uuid4()),
                "type": "GOLDEN" if is_golden else q_type,
                "target": target,
                "target_display": f"擊敗 {target}" if q_type == "BATTLE_WILD" else f"收集 {target}",
                "level": max(1, current_user.level - 5),
                "req": req,
                "now": 0,
                "xp": reward_xp,
                "gold": reward_gold,
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
    current_user.quests = json.dumps(new_quests) # 刪除後，下次 get 會自動補滿
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
        
    # 發放獎勵
    msg = ""
    if target_q.get("type") == "GOLDEN":
        try: inv = json.loads(current_user.inventory) 
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
        
    # 移除已完成任務
    new_quests = [q for q in quests if q["id"] != quest_id]
    current_user.quests = json.dumps(new_quests)
    db.commit()
    
    return {"message": f"任務完成！{msg}"}