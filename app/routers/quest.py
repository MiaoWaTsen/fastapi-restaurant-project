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
    
    # 🔥 V2.11.6 改動：隨時保持 3 個任務
    if len(quests) < 3:
        # 1. 取得玩家當前出戰寵物等級
        target_level = current_user.pet_level
        if target_level < 1: target_level = 1
        if target_level > 96: target_level = 96 # 鎖定上限，避免找不到野怪

        # 2. 找出所有「解鎖等級 <= 目標等級」的野怪，隨機挑一隻
        #    (例如 Lv.5 可以遇到 Lv.1 的小拉達，也可以遇到 Lv.5 的野怪)
        valid_species = []
        for lv in range(1, target_level + 1):
            if lv in WILD_UNLOCK_LEVELS:
                valid_species.extend(WILD_UNLOCK_LEVELS[lv])
        
        # 防呆：如果列表為空 (不太可能發生)，預設小拉達
        if not valid_species: valid_species = ["小拉達"]

        # 補滿到 3 個
        while len(quests) < 3:
            target_mon = random.choice(valid_species)
            
            is_golden = random.random() < 0.05
            
            # 🔥 V2.11.6: 數量與獎勵邏輯
            # 一般任務：1~3 隻
            # 黃金任務：5 隻 (固定)
            
            if is_golden:
                req_count = 5
                reward_desc = "✨ 黃金糖果 x1"
            else:
                req_count = random.randint(1, 3)
                # 獎勵公式：(Base * Count) * Multiplier
                # Base XP = Lv * 30 + 150
                # Base Gold = Lv * 40 + 200
                base_xp = target_level * 30 + 150
                base_gold = target_level * 40 + 200
                
                # 數量加成：1隻=1.0x, 2隻=1.2x (總2.4x), 3隻=1.4x (總4.2x)
                multiplier = 1 + (req_count - 1) * 0.2
                
                total_xp = int(base_xp * req_count * multiplier)
                total_gold = int(base_gold * req_count * multiplier)
                reward_desc = f"{total_xp} XP & {total_gold} Gold"

            new_q = {
                "id": str(uuid.uuid4()),
                "type": "GOLDEN" if is_golden else QUEST_TYPE,
                "target": target_mon,
                "target_display": f"擊敗 {target_mon} (Lv.{target_level})", 
                "level": target_level, # 鎖定等級
                "req": req_count,
                "now": 0,
                "xp": total_xp if not is_golden else 0,
                "gold": total_gold if not is_golden else 0,
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