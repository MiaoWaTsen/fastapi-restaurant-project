# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
import random
import json
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user

router = APIRouter()

# --- 🌲 野怪資料 ---
WILD_DATA = [
    {"name": "卡拉卡拉", "base_hp": 150, "base_xp": 20, "base_gold": 45, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg"},
    {"name": "喵喵", "base_hp": 180, "base_xp": 30, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg"},
    {"name": "皮卡丘", "base_hp": 220, "base_xp": 40, "base_gold": 65, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"},
    {"name": "波波", "base_hp": 200, "base_xp": 50, "base_gold": 75, "img": "https://img.pokemondb.net/artwork/large/pidgey.jpg"},
    {"name": "海星星", "base_hp": 240, "base_xp": 50, "base_gold": 85, "img": "https://img.pokemondb.net/artwork/large/staryu.jpg"}
]

# 升級經驗表
LEVEL_XP = { 1: 50, 2: 100, 3: 200, 4: 350, 5: 600, 6: 1000, 7: 1800, 8: 3000 }

def check_levelup(user: User):
    required_xp = LEVEL_XP.get(user.level, 999999)
    if user.exp >= required_xp:
        user.level += 1
        user.exp -= required_xp
        user.max_hp = int(user.max_hp * 1.4)
        user.hp = user.max_hp 
        user.attack = int(user.attack * 1.2) 
        return True
    return False

# --- API ---

@router.get("/wild")
def get_wild_monsters(current_user: User = Depends(get_current_user)):
    monsters = []
    player_lv = current_user.level
    unlock_count = min(player_lv, len(WILD_DATA))
    monster_id_counter = 1
    
    # 1. 生成固定解鎖的怪
    for i in range(unlock_count):
        m_data = WILD_DATA[i]
        scaling_factor = 1.16 ** (player_lv - 1)
        hp = int(m_data["base_hp"] * scaling_factor)
        base_atk = m_data["base_hp"] * 0.1
        attack = int(base_atk * scaling_factor)
        xp_reward = int(m_data["base_xp"] + (player_lv * 5))
        gold_reward = int(m_data["base_gold"] + (player_lv * 5))

        monsters.append({
            "id": monster_id_counter,
            "name": f"{m_data['name']} (Lv.{player_lv})",
            "hp": hp, "max_hp": hp, "attack": attack,
            "image_url": m_data["img"],
            "xp": xp_reward, "gold": gold_reward
        })
        monster_id_counter += 1
        
    # 2. 額外補怪
    if player_lv > len(WILD_DATA):
        extra_count = player_lv - len(WILD_DATA)
        for _ in range(extra_count):
            m_data = random.choice(WILD_DATA)
            scaling_factor = 1.16 ** (player_lv - 1)
            hp = int(m_data["base_hp"] * scaling_factor)
            base_atk = m_data["base_hp"] * 0.1
            attack = int(base_atk * scaling_factor)
            xp_reward = int(m_data["base_xp"] + (player_lv * 5))
            gold_reward = int(m_data["base_gold"] + (player_lv * 5))
            
            monsters.append({
                "id": monster_id_counter,
                "name": f"{m_data['name']} (Lv.{player_lv})",
                "hp": hp, "max_hp": hp, "attack": attack,
                "image_url": m_data["img"],
                "xp": xp_reward, "gold": gold_reward
            })
            monster_id_counter += 1

    return monsters

class AttackWildSchema(BaseModel):
    monster_name: str
    is_dead: bool

@router.post("/wild/attack")
async def attack_wild(
    data: AttackWildSchema,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    msg = ""
    if data.is_dead:
        base_name = data.monster_name.split('(')[0].strip()
        m_data = next((m for m in WILD_DATA if m["name"] == base_name), WILD_DATA[0])
        
        lv = current_user.level
        xp_gain = int(m_data["base_xp"] + (lv * 5))
        gold_gain = int(m_data["base_gold"] + (lv * 5))
        
        current_user.exp += xp_gain
        current_user.money += gold_gain
        msg = f"擊敗 {data.monster_name}！獲得 {xp_gain} XP, {gold_gain} Gold"
        
        # 🔥 任務進度更新 🔥
        try:
            quests = json.loads(current_user.quests) if current_user.quests else []
            quest_updated = False
            for q in quests:
                # 只有 "ACTIVE" 且 "名字對應" 的任務才更新
                if q["status"] == "ACTIVE" and q["target"] == base_name:
                    if q["now"] < q["req"]:
                        q["now"] += 1
                        quest_updated = True
                        # 檢查是否完成
                        if q["now"] >= q["req"]:
                            q["status"] = "COMPLETED"
                            msg += f" (任務完成！)"
            
            if quest_updated:
                current_user.quests = json.dumps(quests)
        except Exception as e:
            print(f"Quest update error: {e}")

        if check_levelup(current_user):
            msg += f" 🎉 升級了！(Lv.{current_user.level})"
            
        db.add(current_user)
        db.commit()
    
    return {"message": msg, "user": current_user}