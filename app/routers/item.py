# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException, Query
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
WILD_DATA = [
    {"name": "卡拉卡拉", "base_hp": 250, "base_atk": 90, "base_xp": 20, "base_gold": 45, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg"},
    {"name": "喵喵", "base_hp": 280, "base_atk": 100, "base_xp": 30, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg"},
    {"name": "皮卡丘", "base_hp": 300, "base_atk": 110, "base_xp": 40, "base_gold": 65, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"},
    {"name": "波波", "base_hp": 280, "base_atk": 105, "base_xp": 50, "base_gold": 75, "img": "https://img.pokemondb.net/artwork/large/pidgey.jpg"},
    {"name": "海星星", "base_hp": 350, "base_atk": 115, "base_xp": 50, "base_gold": 85, "img": "https://img.pokemondb.net/artwork/large/staryu.jpg"}
]

# 經驗值表
LEVEL_XP = { 1: 50, 2: 100, 3: 200, 4: 350, 5: 600, 6: 1000, 7: 1800, 8: 3000, 9: 5000, 10: 8000 }

# 雙軌升級檢查
def check_levelup_dual(user: User):
    msg_list = []
    
    # 1. 訓練師升級
    req_xp_player = LEVEL_XP.get(user.level, 999999)
    if user.exp >= req_xp_player:
        user.level += 1
        user.exp -= req_xp_player
        msg_list.append(f"訓練師升級(Lv.{user.level})")
        
    # 2. 寶可夢升級 (上限受限於訓練師)
    if user.pet_level < user.level or (user.level == 1 and user.pet_level == 1):
        req_xp_pet = LEVEL_XP.get(user.pet_level, 999999)
        while user.pet_exp >= req_xp_pet:
            if user.pet_level >= user.level: break
            user.pet_level += 1
            user.pet_exp -= req_xp_pet
            user.max_hp = int(user.max_hp * 1.3)
            user.hp = user.max_hp 
            user.attack = int(user.attack * 1.1)
            msg_list.append(f"{user.pokemon_name}升級(Lv.{user.pet_level})")
            req_xp_pet = LEVEL_XP.get(user.pet_level, 999999)
            
    return " & ".join(msg_list) if msg_list else None

# --- API ---

# 1. 取得野怪列表 (支援指定等級)
@router.get("/wild")
def get_wild_monsters(
    level: int = Query(None), # 🔥 新增：允許前端指定等級
    current_user: User = Depends(get_current_user)
):
    monsters = []
    
    # 決定野怪等級：如果有指定且合理，就用指定的；否則用玩家當前等級
    target_lv = level if level else current_user.level
    
    # 防呆/防作弊：不能選超過自己等級的怪，也不能小於1
    if target_lv > current_user.level: target_lv = current_user.level
    if target_lv < 1: target_lv = 1
    
    # 解鎖怪物的種類數量，依然取決於「玩家真實等級」或「目標等級」
    # 這裡設定：若玩家Lv5選Lv2怪，則只出現Lv2該有的怪
    unlock_count = min(target_lv, len(WILD_DATA))
    monster_id_counter = 1
    
    # 1. 生成固定解鎖的怪
    for i in range(unlock_count):
        m_data = WILD_DATA[i]
        
        # 成長係數 (1.2) 使用 target_lv 計算
        scaling_factor = 1.2 ** (target_lv - 1)
        
        hp = int(m_data["base_hp"] * scaling_factor)
        attack = int(m_data["base_atk"] * (1.1 ** (target_lv - 1)))
        
        # 獎勵依據 target_lv 計算
        xp_reward = int(m_data["base_xp"] + (target_lv * 5))
        gold_reward = int(m_data["base_gold"] + (target_lv * 5))

        monsters.append({
            "id": monster_id_counter,
            "name": f"{m_data['name']} (Lv.{target_lv})",
            "hp": hp,
            "max_hp": hp,
            "attack": attack,
            "image_url": m_data["img"],
            "xp": xp_reward,
            "gold": gold_reward
        })
        monster_id_counter += 1
        
    # 2. 額外隨機補怪
    if target_lv > len(WILD_DATA):
        extra_count = target_lv - len(WILD_DATA)
        for _ in range(extra_count):
            m_data = random.choice(WILD_DATA)
            scaling_factor = 1.2 ** (target_lv - 1)
            hp = int(m_data["base_hp"] * scaling_factor)
            attack = int(m_data["base_atk"] * (1.1 ** (target_lv - 1)))
            xp_reward = int(m_data["base_xp"] + (target_lv * 5))
            gold_reward = int(m_data["base_gold"] + (target_lv * 5))
            
            monsters.append({
                "id": monster_id_counter,
                "name": f"{m_data['name']} (Lv.{target_lv})",
                "hp": hp, "max_hp": hp, "attack": attack,
                "image_url": m_data["img"],
                "xp": xp_reward, "gold": gold_reward
            })
            monster_id_counter += 1

    return monsters

class AttackWildSchema(BaseModel):
    monster_name: str
    is_dead: bool
    level: int # 🔥 新增：告知後端打死的是幾等的怪

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
        
        # 🔥 使用前端傳來的怪物等級計算獎勵 (防止打Lv1拿Lv10獎勵) 🔥
        # 同時做個檢查，不能超過玩家等級
        monster_lv = data.level
        if monster_lv > current_user.level: monster_lv = current_user.level
        if monster_lv < 1: monster_lv = 1
        
        xp_gain = int(m_data["base_xp"] + (monster_lv * 5))
        gold_gain = int(m_data["base_gold"] + (monster_lv * 5))
        
        current_user.exp += xp_gain
        current_user.pet_exp += xp_gain
        current_user.money += gold_gain
        
        msg = f"擊敗 {data.monster_name}！獲得 {xp_gain} XP, {gold_gain} Gold"
        
        lvl_msg = check_levelup_dual(current_user)
        if lvl_msg: msg += f" 🎉 {lvl_msg}！"
            
        try:
            quests = json.loads(current_user.quests) if current_user.quests else []
            quest_updated = False
            for q in quests:
                # 這裡可能需要判斷等級是否符合任務需求，目前暫不嚴格限制
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