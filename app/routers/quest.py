# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
import json
import uuid

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user
from app.routers.shop import WILD_UNLOCK_LEVELS  # 引用解鎖表
# 為了避免循環引用，我們在這裡重新定義或從 common 引用簡單的配置
# 這裡簡單起見，我們再次定義解鎖表，或者您應該將這些配置移到 app/core/config.py

router = APIRouter()

# 為了方便，這裡保留一份解鎖表副本，實際專案應放在 config.py
WILD_UNLOCK_LEVELS_REF = {
    1: ["小拉達"], 2: ["波波"], 3: ["烈雀"], 4: ["阿柏蛇"], 5: ["瓦斯彈"],
    6: ["海星星"], 7: ["角金魚"], 8: ["走路草"], 9: ["穿山鼠"], 10: ["蚊香蝌蚪"],
    12: ["小磁怪"], 14: ["卡拉卡拉"], 16: ["喵喵"], 18: ["瑪瑙水母"], 20: ["海刺龍"]
}

def generate_quests(user_level, count=3):
    new_quests = []
    targets_pool = []
    # 根據 user_level 找出所有可解鎖的怪
    for u_lv, species in WILD_UNLOCK_LEVELS_REF.items():
        if u_lv <= user_level:
            targets_pool.extend(species)
            
    if not targets_pool:
        targets_pool = ["小拉達"]
    
    for _ in range(count):
        target = random.choice(targets_pool)
        # 數量隨機 1 ~ 3 + (等級/3)
        req_count = random.randint(1, 3) + int(user_level/3)
        is_golden = random.random() < 0.03 # 3% 黃金任務
        
        if is_golden:
            q = {
                "id": str(uuid.uuid4()),
                "type": "GOLDEN",
                "target": "野怪",
                "target_display": "Lv.? 野怪",
                "target_lv": user_level,
                "req": 5,
                "now": 0,
                "gold": 0,
                "xp": 0,
                "status": "WAITING"
            }
        else:
            # 獎勵係數 V2.0.2 設定: Gold * 50, XP * 30
            gold_reward = req_count * 50
            xp_reward = req_count * 30
            
            q = {
                "id": str(uuid.uuid4()),
                "type": "NORMAL",
                "target": target,
                "target_display": f"Lv.{user_level} {target}",
                "target_lv": user_level,
                "req": req_count,
                "now": 0,
                "gold": gold_reward,
                "xp": xp_reward,
                "status": "WAITING"
            }
        new_quests.append(q)
    return new_quests

@router.get("/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quests = json.loads(current_user.quests) if current_user.quests else []
    
    # 檢查是否為舊格式 (沒有 target_display) -> 強制重置
    need_reset = False
    if not quests:
        need_reset = True
    else:
        for q in quests:
            if "target_display" not in q:
                need_reset = True
                break
    
    if need_reset:
        quests = generate_quests(current_user.level, count=3)
        current_user.quests = json.dumps(quests)
        db.commit()
        return quests

    # 補齊任務到 3 個
    active_or_waiting = [q for q in quests if q["status"] in ["ACTIVE", "WAITING"]]
    needed = 3 - len(active_or_waiting)
    
    if needed > 0:
        new_qs = generate_quests(current_user.level, count=needed)
        # 只保留有效任務 + 新任務
        final_list = active_or_waiting + new_qs
        current_user.quests = json.dumps(final_list)
        db.commit()
        return final_list
        
    return active_or_waiting

@router.post("/accept/{qid}")
def accept_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quests = json.loads(current_user.quests)
    for q in quests:
        if q["id"] == qid and q["status"] == "WAITING":
            q["status"] = "ACTIVE"
            current_user.quests = json.dumps(quests)
            db.commit()
            return {"message": "任務已接受"}
    raise HTTPException(status_code=400, detail="無法接受此任務")

@router.post("/abandon/{qid}")
def abandon_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 1000:
        raise HTTPException(status_code=400, detail="刪除任務需 1000 Gold")
    
    quests = json.loads(current_user.quests)
    # 移除目標任務
    new_quests = [q for q in quests if q["id"] != qid]
    
    if len(new_quests) == len(quests):
        raise HTTPException(status_code=404, detail="找不到任務")
    
    current_user.money -= 1000
    # 補一個新任務
    new_q = generate_quests(current_user.level, count=1)[0]
    new_quests.append(new_q)
    
    current_user.quests = json.dumps(new_quests)
    db.commit()
    return {"message": "任務已刪除並刷新 (-1000G)"}

@router.post("/claim/{qid}")
def claim_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quests = json.loads(current_user.quests)
    inv = json.loads(current_user.inventory)
    
    target_q = None
    # 尋找已完成的任務
    for q in quests:
        if q["id"] == qid and q["status"] == "COMPLETED":
            target_q = q
            break
            
    if not target_q:
        raise HTTPException(status_code=400, detail="無法領取：任務不存在或未完成")
    
    msg = ""
    if target_q["type"] == "GOLDEN":
        inv["golden_candy"] = inv.get("golden_candy", 0) + 1
        msg = "獲得 ✨ 黃金糖果 x1"
    else:
        current_user.money += target_q["gold"]
        current_user.exp += target_q["xp"]
        current_user.pet_exp += target_q["xp"]
        msg = f"獲得 {target_q['gold']}G, {target_q['xp']} XP"
    
    # 移除該任務
    quests = [q for q in quests if q["id"] != qid]
    # 補一個新任務
    new_q = generate_quests(current_user.level, count=1)[0]
    quests.append(new_q)
    
    current_user.quests = json.dumps(quests)
    current_user.inventory = json.dumps(inv)
    db.commit()
    
    return {"message": msg}