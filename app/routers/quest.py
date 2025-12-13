# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
import json
from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user
from app.common.websocket import manager # 🔥 新增 manager 引用

router = APIRouter()

WILD_DB_REF = [
    { "min_lv": 1, "name": "小拉達" }, { "min_lv": 2, "name": "波波" },
    { "min_lv": 3, "name": "烈雀" }, { "min_lv": 4, "name": "阿柏蛇" },
    { "min_lv": 5, "name": "瓦斯彈" }, { "min_lv": 6, "name": "海星星" },
    { "min_lv": 7, "name": "角金魚" }, { "min_lv": 8, "name": "走路草" },
    { "min_lv": 9, "name": "穿山鼠" }, { "min_lv": 10, "name": "蚊香勇士", "is_boss": True },
    { "min_lv": 12, "name": "小磁怪" }, { "min_lv": 14, "name": "卡拉卡拉" },
    { "min_lv": 16, "name": "喵喵" }, { "min_lv": 18, "name": "瑪瑙水母" },
    { "min_lv": 20, "name": "暴鯉龍", "is_boss": True }
]

# 🔥 複製升級邏輯，確保任務獲得經驗也能觸發升級 🔥
LEVEL_XP = { 
    1: 50, 2: 150, 3: 300, 4: 500, 5: 800, 
    6: 1300, 7: 2000, 8: 3000, 9: 5000 
}

def get_req_xp(lv):
    if lv >= 25: return 999999999
    if lv < 10: return LEVEL_XP.get(lv, 5000)
    return 5000 + (lv - 9) * 2000

async def check_levelup_dual(user: User):
    msg_list = []
    
    # 1. 訓練師升級
    req_xp_player = get_req_xp(user.level)
    if user.exp >= req_xp_player and user.level < 25:
        user.level += 1
        user.exp -= req_xp_player
        msg_list.append(f"訓練師升級(Lv.{user.level})")
        await manager.broadcast(f"📢 恭喜玩家 [{user.username}] 提升到了 訓練師等級 {user.level}！")
        
    # 2. 寶可夢升級
    if (user.pet_level < user.level or (user.level == 1 and user.pet_level == 1)) and user.pet_level < 25:
        req_xp_pet = get_req_xp(user.pet_level)
        while user.pet_exp >= req_xp_pet:
            if user.pet_level >= user.level and user.level > 1: break
            if user.pet_level >= 25: break 
            
            user.pet_level += 1
            user.pet_exp -= req_xp_pet
            
            # 數值成長 (與 item.py 保持一致: 攻*1.06, 血*1.08)
            user.max_hp = int(user.max_hp * 1.08)
            user.hp = user.max_hp
            user.attack = int(user.attack * 1.06)
            
            msg_list.append(f"{user.pokemon_name}升級(Lv.{user.pet_level})")
            req_xp_pet = get_req_xp(user.pet_level)
            
    return " & ".join(msg_list) if msg_list else None

@router.get("/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try: quest_list = json.loads(current_user.quests) if current_user.quests else []
    except: quest_list = []

    changed = False
    while len(quest_list) < 3:
        defeated = current_user.defeated_bosses.split(',') if current_user.defeated_bosses else []
        valid_targets = [
            m for m in WILD_DB_REF 
            if m["min_lv"] <= current_user.level and (not m.get("is_boss") or m["name"] not in defeated)
        ]
        
        if not valid_targets: break 
        
        is_golden = random.random() < 0.03
        target = random.choice(valid_targets)
        target_lv = current_user.level 
        
        if is_golden:
            count = 5; reward_gold = 0; reward_xp = 0; q_type = "GOLDEN"
        else:
            count = 1 if target.get("is_boss") else random.randint(1, 3)
            reward_base = 100 if target.get("is_boss") else 50
            count_bonus = 1 + (count - 1) * 0.1
            reward_gold = int(reward_base * count * count_bonus * (target_lv/2 + 1))
            reward_xp = int(reward_base * count * count_bonus * (target_lv/2 + 1))
            q_type = "NORMAL"
        
        new_quest = {
            "id": random.randint(10000, 99999),
            "target": target["name"],
            "target_lv": target_lv,
            "req": count, "now": 0, "gold": reward_gold, "xp": reward_xp,
            "status": "WAITING", "type": q_type
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
    active_quests = [q for q in quest_list if q["status"] == "ACTIVE"]
    if len(active_quests) >= 1:
        raise HTTPException(status_code=400, detail="一次只能進行一個任務！")

    for q in quest_list:
        if q["id"] == quest_id and q["status"] == "WAITING":
            q["status"] = "ACTIVE"
            current_user.quests = json.dumps(quest_list)
            db.commit()
            return {"message": "任務已接受"}
            
    raise HTTPException(status_code=400, detail="任務不存在")

# 🔥 改為 async 以便執行 await check_levelup_dual 🔥
@router.post("/claim/{quest_id}")
async def claim_quest(quest_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quest_list = json.loads(current_user.quests)
    new_list = []
    claimed = False
    msg = ""
    
    for q in quest_list:
        if q["id"] == quest_id and q["status"] == "COMPLETED":
            if q.get("type") == "GOLDEN":
                inventory = json.loads(current_user.inventory) if current_user.inventory else {}
                inventory["golden_candy"] = inventory.get("golden_candy", 0) + 1
                current_user.inventory = json.dumps(inventory)
                msg = "領取成功！獲得 🍬 黃金糖果！"
            else:
                current_user.money += q["gold"]
                current_user.exp += q["xp"]
                current_user.pet_exp += q["xp"]
                msg = f"領取成功！獲得 {q['gold']} G, {q['xp']} XP"
            
            claimed = True
            continue 
        new_list.append(q)
        
    if not claimed: raise HTTPException(status_code=400, detail="無法領取")
    
    # 🔥 立即檢查升級 🔥
    lvl_msg = await check_levelup_dual(current_user)
    if lvl_msg: msg += f" 🎉 {lvl_msg}！"

    current_user.quests = json.dumps(new_list)
    db.commit()
    return {"message": msg, "user": current_user}