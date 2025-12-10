# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
import json

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user
# 這裡不需要 check_levelup，因為領獎勵只給錢和經驗，升級由 check_levelup_dual_local 處理 (避免循環)

router = APIRouter()

# 引用野怪表 (為了生成任務)
WILD_DB = [
    { "min_lv": 1, "name": "小拉達" }, { "min_lv": 2, "name": "波波" },
    { "min_lv": 3, "name": "烈雀" }, { "min_lv": 4, "name": "阿柏蛇" },
    { "min_lv": 5, "name": "瓦斯彈" }, { "min_lv": 6, "name": "海星星" },
    { "min_lv": 7, "name": "角金魚" }, { "min_lv": 8, "name": "走路草" },
    { "min_lv": 9, "name": "穿山鼠" }, { "min_lv": 10, "name": "蚊香勇士" },
    { "min_lv": 12, "name": "小磁怪" }, { "min_lv": 14, "name": "卡拉卡拉" },
    { "min_lv": 16, "name": "喵喵" }, { "min_lv": 18, "name": "瑪瑙水母" },
    { "min_lv": 20, "name": "暴鯉龍" }
]

@router.get("/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try: quest_list = json.loads(current_user.quests) if current_user.quests else []
    except: quest_list = []

    changed = False
    # 保持三個任務
    while len(quest_list) < 3:
        # 隨機挑選一個玩家等級能遇到的怪 (min_lv <= player_lv)
        valid_targets = [m for m in WILD_DB if m["min_lv"] <= current_user.level]
        if not valid_targets: break # 異常狀況
        
        target = random.choice(valid_targets)
        # 任務目標等級：就是該怪物的出場等級 (或玩家當前等級，這裡設定為怪物出場等級較合理，或者玩家等級)
        # PDF 需求：擊敗 X 級的 XX，要合理
        # 我們設定目標等級為：該怪物的 min_lv (確保玩家一定能遇到)
        target_lv = target["min_lv"] 
        
        count = random.randint(1, 3)
        reward_gold = int(50 * count * (target_lv/2 + 1))
        reward_xp = int(30 * count * (target_lv/2 + 1))
        
        new_quest = {
            "id": random.randint(10000, 99999),
            "target": target["name"],
            "target_lv": target_lv,
            "req": count, "now": 0, "gold": reward_gold, "xp": reward_xp,
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
    
    # 🔥 限制：一次只能接一個任務 🔥
    active_quests = [q for q in quest_list if q["status"] == "ACTIVE"]
    if len(active_quests) >= 1:
        raise HTTPException(status_code=400, detail="一次只能進行一個任務！請先完成或放棄當前任務。")

    for q in quest_list:
        if q["id"] == quest_id and q["status"] == "WAITING":
            q["status"] = "ACTIVE"
            current_user.quests = json.dumps(quest_list)
            db.commit()
            return {"message": "任務已接受"}
            
    raise HTTPException(status_code=400, detail="任務不存在")

@router.post("/claim/{quest_id}")
def claim_quest(quest_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quest_list = json.loads(current_user.quests)
    new_list = []
    claimed = False
    msg = ""
    
    for q in quest_list:
        if q["id"] == quest_id and q["status"] == "COMPLETED":
            current_user.money += q["gold"]
            current_user.exp += q["xp"]
            current_user.pet_exp += q["xp"]
            msg = f"領取成功！獲得 {q['gold']} G, {q['xp']} XP"
            claimed = True
            # 這裡不處理升級廣播，簡化邏輯，或者可以 copy check_levelup_dual 邏輯
            continue
        new_list.append(q)
        
    if not claimed: raise HTTPException(status_code=400, detail="無法領取")
    current_user.quests = json.dumps(new_list)
    db.commit()
    return {"message": msg, "user": current_user}