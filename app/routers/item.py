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

# --- 🌲 野怪資料 (平衡版 V3) ---
# 配合 (Atk/100)*Move 公式，野怪血量需提升至 250~400 左右才耐打
WILD_DATA = [
    {"name": "卡拉卡拉", "base_hp": 250, "base_atk": 90, "base_xp": 20, "base_gold": 45, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg"},
    {"name": "喵喵", "base_hp": 280, "base_atk": 100, "base_xp": 30, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg"},
    {"name": "皮卡丘", "base_hp": 300, "base_atk": 110, "base_xp": 40, "base_gold": 65, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"},
    {"name": "波波", "base_hp": 280, "base_atk": 105, "base_xp": 50, "base_gold": 75, "img": "https://img.pokemondb.net/artwork/large/pidgey.jpg"},
    {"name": "海星星", "base_hp": 350, "base_atk": 115, "base_xp": 50, "base_gold": 85, "img": "https://img.pokemondb.net/artwork/large/staryu.jpg"}
]

# 經驗值表 (1~10級)
LEVEL_XP = { 1: 50, 2: 100, 3: 200, 4: 350, 5: 600, 6: 1000, 7: 1800, 8: 3000, 9: 5000, 10: 8000 }

# 🔥 雙軌升級檢查 🔥
def check_levelup_dual(user: User):
    msg_list = []
    
    # 1. 訓練師升級 (決定上限)
    req_xp_player = LEVEL_XP.get(user.level, 999999)
    if user.exp >= req_xp_player:
        user.level += 1
        user.exp -= req_xp_player
        msg_list.append(f"訓練師升級(Lv.{user.level})")
        
    # 2. 寶可夢升級 (能力成長)
    # 限制: 寶可夢等級不能超過訓練師 (除非訓練師也是Lv1)
    if user.pet_level < user.level or (user.level == 1 and user.pet_level == 1):
        req_xp_pet = LEVEL_XP.get(user.pet_level, 999999)
        # 循環升級 (防止一次獲得大量經驗時只升一級)
        while user.pet_exp >= req_xp_pet:
            # 再次檢查上限
            if user.pet_level >= user.level:
                break
                
            user.pet_level += 1
            user.pet_exp -= req_xp_pet
            
            # 能力成長: 血量*1.3, 攻擊*1.1
            user.max_hp = int(user.max_hp * 1.3)
            user.hp = user.max_hp # 升級補滿
            user.attack = int(user.attack * 1.1)
            
            msg_list.append(f"{user.pokemon_name}升級(Lv.{user.pet_level})")
            
            # 更新下一級需求
            req_xp_pet = LEVEL_XP.get(user.pet_level, 999999)
            
    return " & ".join(msg_list) if msg_list else None

# --- API ---

@router.get("/wild")
def get_wild_monsters(current_user: User = Depends(get_current_user)):
    monsters = []
    # 野怪等級跟隨「訓練師等級」
    player_lv = current_user.level
    unlock_count = min(player_lv, len(WILD_DATA))
    monster_id_counter = 1
    
    # 1. 生成固定解鎖的怪
    for i in range(unlock_count):
        m_data = WILD_DATA[i]
        
        # 成長係數 (1.2)
        scaling_factor = 1.2 ** (player_lv - 1)
        
        hp = int(m_data["base_hp"] * scaling_factor)
        attack = int(m_data["base_atk"] * (1.1 ** (player_lv - 1))) 
        
        xp_reward = int(m_data["base_xp"] + (player_lv * 5))
        gold_reward = int(m_data["base_gold"] + (player_lv * 5))

        monsters.append({
            "id": monster_id_counter,
            "name": f"{m_data['name']} (Lv.{player_lv})",
            "hp": hp,
            "max_hp": hp,
            "attack": attack,
            "image_url": m_data["img"],
            "xp": xp_reward,
            "gold": gold_reward
        })
        monster_id_counter += 1
        
    # 2. 額外隨機補怪 (保持野區豐富)
    if player_lv > len(WILD_DATA):
        extra_count = player_lv - len(WILD_DATA)
        for _ in range(extra_count):
            m_data = random.choice(WILD_DATA)
            scaling_factor = 1.2 ** (player_lv - 1)
            hp = int(m_data["base_hp"] * scaling_factor)
            attack = int(m_data["base_atk"] * (1.1 ** (player_lv - 1)))
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
        # 解析名字取出基礎名
        base_name = data.monster_name.split('(')[0].strip()
        # 簡單查找基礎資料
        m_data = next((m for m in WILD_DATA if m["name"] == base_name), WILD_DATA[0])
        
        lv = current_user.level
        xp_gain = int(m_data["base_xp"] + (lv * 5))
        gold_gain = int(m_data["base_gold"] + (lv * 5))
        
        # 🔥 雙軌經驗獲得 🔥
        current_user.exp += xp_gain        # 訓練師經驗
        current_user.pet_exp += xp_gain    # 寶可夢經驗
        current_user.money += gold_gain
        
        msg = f"擊敗 {data.monster_name}！獲得 {xp_gain} XP, {gold_gain} Gold"
        
        # 檢查升級
        lvl_msg = check_levelup_dual(current_user)
        if lvl_msg:
            msg += f" 🎉 {lvl_msg}！"
            
        # 任務進度更新 (保持不變)
        try:
            quests = json.loads(current_user.quests) if current_user.quests else []
            quest_updated = False
            for q in quests:
                if q["status"] == "ACTIVE" and q["target"] == base_name:
                    if q["now"] < q["req"]:
                        q["now"] += 1
                        quest_updated = True
                        if q["now"] >= q["req"]: q["status"] = "COMPLETED"; msg += " (任務完成!)"
            if quest_updated: current_user.quests = json.dumps(quests)
        except: pass

        db.add(current_user)
        db.commit()
    
    return {"message": msg, "user": current_user}