# app/routers/quests.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import random

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.routers.shop import POKEDEX_DATA, WILD_UNLOCK_LEVELS 

router = APIRouter()

# 🔥 新版獎勵公式 (保留您要的高獎勵機制) 🔥
def calc_reward(target_name, level, count, is_golden):
    # 1. 種族值差異 (讓波波 > 小拉達)
    base_data = POKEDEX_DATA.get(target_name, {"hp": 100, "atk": 100})
    species_score = (base_data.get("hp", 100) + base_data.get("atk", 100)) / 4
    
    # 2. 等級加成 (非線性，等級越高加成越多)
    level_mult = 1 + (level * 0.15) 
    
    # 3. 數量加成 (擊殺多隻有額外 Bonus)
    # 1隻 = 1.0倍, 2隻 = 2.4倍 (2*1.2), 3隻 = 3.9倍 (3*1.3)
    quantity_bonus = 1.0 + ((count - 1) * 0.2) if count > 1 else 1.0
    
    # 基礎金幣計算
    base_gold = species_score * level_mult * count * quantity_bonus
    
    # 黃金任務加成 (5倍)
    if is_golden:
        base_gold *= 5
    
    # 加上隨機浮動 (0.9 ~ 1.1)
    final_gold = int(base_gold * random.uniform(0.9, 1.1))
    
    # 經驗值約為金幣的 80%
    final_xp = int(final_gold * 0.8)
    
    # 確保最低值
    if final_gold < 10: final_gold = 10
    if final_xp < 10: final_xp = 10
    
    return final_gold, final_xp

@router.get("/")
def get_quests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quests = []
    if current_user.quests:
        try:
            quests = json.loads(current_user.quests)
        except:
            quests = []
            
    # 如果任務不滿 3 個，補滿
    if len(quests) < 3:
        candidate_pool = []
        
        # 🔥 關鍵修正：使用「寵物等級」作為上限，而非玩家等級 🔥
        # 這樣練新寵時，只會接到該等級區間的怪
        max_pool_level = current_user.pet_level
        if max_pool_level < 1: max_pool_level = 1
        
        # 建立候選池：累積解鎖 (1 ~ current_user.pet_level)
        for lv in range(1, max_pool_level + 1):
            species = WILD_UNLOCK_LEVELS.get(lv)
            # 向下相容邏輯 (如果該等級沒定義怪，往前找)
            if not species:
                for prev_lv in range(lv - 1, 0, -1):
                    if prev_lv in WILD_UNLOCK_LEVELS:
                        species = WILD_UNLOCK_LEVELS[prev_lv]
                        break
            if not species: species = ["小拉達"]
            candidate_pool.extend(species)
        
        candidate_pool = list(set(candidate_pool))
        
        needed = 3 - len(quests)
        for _ in range(needed):
            target_name = random.choice(candidate_pool)
            
            # 目標等級固定為玩家寵物等級
            target_level = current_user.pet_level
            if target_level < 1: target_level = 1
            
            is_golden = random.random() < 0.05
            req_count = 1 if is_golden else random.randint(1, 3)
            
            # 使用新公式計算獎勵
            gold, xp = calc_reward(target_name, target_level, req_count, is_golden)
            
            new_quest = {
                "id": str(random.randint(10000, 99999)),
                "target": target_name,
                "target_display": f"討伐 Lv.{target_level} {target_name}",
                "level": target_level, # 用於前端顯示或後端驗證
                "req": req_count,
                "now": 0,
                "gold": gold,
                "xp": xp,
                "type": "GOLDEN" if is_golden else "NORMAL",
                "status": "ACTIVE"
            }
            quests.append(new_quest)
            
        current_user.quests = json.dumps(quests)
        db.commit()
        
    return quests

@router.post("/claim/{quest_id}")
def claim_quest(quest_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quests = json.loads(current_user.quests)
    target_q = next((q for q in quests if q["id"] == quest_id), None)
    
    if not target_q:
        raise HTTPException(status_code=404, detail="找不到任務")
        
    if target_q["now"] < target_q["req"]:
        raise HTTPException(status_code=400, detail="任務尚未完成")
        
    # 發放獎勵
    current_user.money += target_q["gold"]
    current_user.exp += target_q["xp"]
    current_user.pet_exp += target_q["xp"]
    
    if target_q["type"] == "GOLDEN":
        inv = json.loads(current_user.inventory)
        inv["golden_candy"] = inv.get("golden_candy", 0) + 1
        current_user.inventory = json.dumps(inv)
        
    # 移除已完成任務
    quests = [q for q in quests if q["id"] != quest_id]
    current_user.quests = json.dumps(quests)
    db.commit()
    
    return {"message": f"任務完成！獲得 {target_q['gold']}G, {target_q['xp']}XP"}

@router.post("/abandon/{quest_id}")
def abandon_quest(quest_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.money < 1000:
        raise HTTPException(status_code=400, detail="金幣不足 1000G")
        
    quests = json.loads(current_user.quests)
    new_quests = [q for q in quests if q["id"] != quest_id]
    
    if len(new_quests) == len(quests):
        raise HTTPException(status_code=404, detail="找不到任務")
        
    current_user.money -= 1000
    current_user.quests = json.dumps(new_quests)
    db.commit()
    
    return {"message": "已放棄任務 (消耗 1000G)"}