# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
import json
import uuid
from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user

router = APIRouter()

# 這裡必須跟 shop.py 的 WILD_UNLOCK_LEVELS 一致
WILD_UNLOCK_LEVELS_REF = {
    1: ["小拉達"], 2: ["波波"], 3: ["烈雀"], 4: ["阿柏蛇"], 5: ["瓦斯彈"],
    6: ["海星星"], 7: ["角金魚"], 8: ["走路草"], 9: ["穿山鼠"], 10: ["蚊香蝌蚪"],
    12: ["小磁怪"], 14: ["卡拉卡拉"], 16: ["喵喵"], 18: ["瑪瑙水母"], 20: ["海刺龍"]
}

def generate_single_quest(pet_level: int):
    # 🔥 1. 嚴格模式：只從該等級的池子裡挑
    # 如果該等級沒有對應野怪 (例如 Lv.11)，則往下找最近的等級
    target_pool = WILD_UNLOCK_LEVELS_REF.get(pet_level)
    target_level = pet_level
    
    if not target_pool:
        # 找不到對應等級，往下搜尋
        for lv in sorted(WILD_UNLOCK_LEVELS_REF.keys(), reverse=True):
            if lv < pet_level:
                target_pool = WILD_UNLOCK_LEVELS_REF[lv]
                target_level = lv
                break
    
    if not target_pool: 
        target_pool = ["小拉達"]
        target_level = 1
        
    target = random.choice(target_pool)
    
    is_golden = random.random() < 0.03
    
    if is_golden:
        return {
            "id": str(uuid.uuid4()),
            "type": "GOLDEN",
            "target": target,
            "level": target_level, # 🔥 紀錄目標等級
            "target_display": f"✨ 討伐 Lv.{target_level} {target} (黃金)",
            "req": 5,
            "now": 0,
            "gold": 0, "xp": 0, "item": "golden_candy",
            "status": "IN_PROGRESS"
        }
    else:
        req = random.randint(1, 3)
        return {
            "id": str(uuid.uuid4()),
            "type": "NORMAL",
            "target": target,
            "level": target_level, # 🔥 紀錄目標等級
            "target_display": f"討伐 Lv.{target_level} {target}",
            "req": req,
            "now": 0,
            "gold": req * 50, "xp": req * 30, "item": None,
            "status": "IN_PROGRESS"
        }

@router.get("/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        quests = json.loads(current_user.quests) if current_user.quests else []
    except:
        quests = []
    
    if len(quests) < 3:
        needed = 3 - len(quests)
        pet_lv = current_user.pet_level if current_user.pet_level else 1
        for _ in range(needed):
            quests.append(generate_single_quest(pet_lv))
        current_user.quests = json.dumps(quests)
        db.commit()
        
    return quests

@router.post("/abandon/{qid}")
def abandon_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 1000:
        raise HTTPException(status_code=400, detail="餘額不足 1000G")
    
    quests = json.loads(current_user.quests)
    new_list = [q for q in quests if q["id"] != qid]
    
    # 立即補一個新的
    new_list.append(generate_single_quest(current_user.pet_level))
    
    current_user.money -= 1000
    current_user.quests = json.dumps(new_list)
    db.commit()
    return {"message": "已更換新任務 (-1000G)"}

@router.post("/claim/{qid}")
def claim_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quests = json.loads(current_user.quests)
    try:
        inv = json.loads(current_user.inventory) if current_user.inventory else {}
    except:
        inv = {}
        
    target_q = next((q for q in quests if q["id"] == qid), None)
    if not target_q or target_q["now"] < target_q["req"]:
        raise HTTPException(status_code=400, detail="尚未達成條件")

    msg = ""
    if target_q["type"] == "GOLDEN":
        inv["golden_candy"] = inv.get("golden_candy", 0) + 1
        msg = "獲得 ✨ 黃金糖果 x1"
    else:
        current_user.money += target_q["gold"]
        current_user.exp += target_q["xp"]
        current_user.pet_exp += target_q["xp"]
        msg = f"獲得 {target_q['gold']}G, {target_q['xp']} XP"

    # 刪除舊的，補一個新的
    quests = [q for q in quests if q["id"] != qid]
    quests.append(generate_single_quest(current_user.pet_level))
    
    current_user.quests = json.dumps(quests)
    current_user.inventory = json.dumps(inv)
    db.commit()
    return {"message": msg}