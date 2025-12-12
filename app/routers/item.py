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
from app.common.websocket import manager

router = APIRouter()

# --- 🌲 野怪資料 (PDF Source 205-219) ---
WILD_DB = [
    { "min_lv": 1, "name": "小拉達", "base_hp": 90, "base_atk": 80, "img": "https://img.pokemondb.net/artwork/large/rattata.jpg" },
    { "min_lv": 2, "name": "波波", "base_hp": 94, "base_atk": 84, "img": "https://img.pokemondb.net/artwork/large/pidgey.jpg" },
    { "min_lv": 3, "name": "烈雀", "base_hp": 88, "base_atk": 92, "img": "https://img.pokemondb.net/artwork/large/spearow.jpg" },
    { "min_lv": 4, "name": "阿柏蛇", "base_hp": 98, "base_atk": 90, "img": "https://img.pokemondb.net/artwork/large/ekans.jpg" },
    { "min_lv": 5, "name": "瓦斯彈", "base_hp": 108, "base_atk": 100, "img": "https://img.pokemondb.net/artwork/large/koffing.jpg" },
    { "min_lv": 6, "name": "海星星", "base_hp": 120, "base_atk": 95, "img": "https://img.pokemondb.net/artwork/large/staryu.jpg" },
    { "min_lv": 7, "name": "角金魚", "base_hp": 125, "base_atk": 100, "img": "https://img.pokemondb.net/artwork/large/goldeen.jpg" },
    { "min_lv": 8, "name": "走路草", "base_hp": 120, "base_atk": 110, "img": "https://img.pokemondb.net/artwork/large/oddish.jpg" },
    { "min_lv": 9, "name": "穿山鼠", "base_hp": 120, "base_atk": 110, "img": "https://img.pokemondb.net/artwork/large/sandshrew.jpg" },
    { "min_lv": 10, "name": "蚊香勇士", "base_hp": 150, "base_atk": 140, "img": "https://img.pokemondb.net/artwork/large/poliwrath.jpg", "is_boss": True },
    { "min_lv": 12, "name": "小磁怪", "base_hp": 120, "base_atk": 114, "img": "https://img.pokemondb.net/artwork/large/magnemite.jpg" },
    { "min_lv": 14, "name": "卡拉卡拉", "base_hp": 120, "base_atk": 120, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg" },
    { "min_lv": 16, "name": "喵喵", "base_hp": 124, "base_atk": 124, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg" },
    { "min_lv": 18, "name": "瑪瑙水母", "base_hp": 130, "base_atk": 130, "img": "https://img.pokemondb.net/artwork/large/tentacool.jpg" },
    { "min_lv": 20, "name": "暴鯉龍", "base_hp": 160, "base_atk": 180, "img": "https://img.pokemondb.net/artwork/large/gyarados.jpg", "is_boss": True },
]

LEVEL_XP = { 1: 50, 2: 120, 3: 240, 4: 400, 5: 600, 6: 900, 7: 1350, 8: 2000, 9: 3000 }

async def check_levelup_dual(user: User):
    msg_list = []
    def get_req_xp(lv): return LEVEL_XP.get(lv, 3000) if lv < 10 else 3000 + (lv - 10) * 1000

    # 1. 訓練師升級
    req_xp_player = get_req_xp(user.level)
    if user.exp >= req_xp_player:
        user.level += 1
        user.exp -= req_xp_player
        msg_list.append(f"訓練師升級(Lv.{user.level})")
        await manager.broadcast(f"📢 恭喜玩家 [{user.username}] 提升到了 訓練師等級 {user.level}！")
        
    # 2. 寶可夢升級
    if user.pet_level < user.level or (user.level == 1 and user.pet_level == 1):
        req_xp_pet = get_req_xp(user.pet_level)
        while user.pet_exp >= req_xp_pet:
            if user.pet_level >= user.level and user.level > 1: break 
            user.pet_level += 1
            user.pet_exp -= req_xp_pet
            user.max_hp = int(user.max_hp * 1.06)
            user.hp = user.max_hp
            user.attack = int(user.attack * 1.12)
            msg_list.append(f"{user.pokemon_name}升級(Lv.{user.pet_level})")
            req_xp_pet = get_req_xp(user.pet_level)
            
    return " & ".join(msg_list) if msg_list else None

@router.get("/wild")
def get_wild_monsters(
    level: int = Query(None), 
    current_user: User = Depends(get_current_user)
):
    monsters = []
    player_lv = current_user.level
    
    target_lv = level if level else player_lv
    if target_lv > player_lv: target_lv = player_lv

    defeated = current_user.defeated_bosses.split(',') if current_user.defeated_bosses else []
    
    available = []
    for m in WILD_DB:
        if m["min_lv"] <= target_lv:
            if m.get("is_boss") and m["name"] in defeated: continue
            available.append(m)

    monster_id_counter = 1
    display_list = []
    if len(available) > 6:
        # 隨機選，權重偏向高等級
        display_list = random.sample(available, 6)
        display_list.sort(key=lambda x: x["min_lv"])
    else:
        display_list = available

    for m_data in display_list:
        is_boss = m_data.get("is_boss", False)
        
        if is_boss:
            final_lv = m_data["min_lv"]
            hp = m_data["base_hp"]
            attack = m_data["base_atk"]
        else:
            final_lv = target_lv
            hp_scale = 1.06 ** (final_lv - 1)
            atk_scale = 1.12 ** (final_lv - 1)
            # 🔥 血量提升 1.3 倍, 攻擊力提升 1.35 倍 (修正) 🔥
            hp = int(m_data["base_hp"] * hp_scale * 1.3)
            attack = int(m_data["base_atk"] * atk_scale * 1.35)
        
        # 🔥 賞金機制更新：基礎值 + (min_lv * 3) + (current_lv * 5) 🔥
        base_bonus = m_data["min_lv"] * 3
        xp_reward = int(20 + base_bonus + final_lv * 5)
        gold_reward = int(45 + base_bonus + final_lv * 5)
        
        if is_boss:
            xp_reward *= 3
            gold_reward *= 3

        monsters.append({
            "id": monster_id_counter,
            "name": f"{m_data['name']} (Lv.{final_lv})" + (" 👑" if is_boss else ""),
            "hp": hp, "max_hp": hp, "attack": attack,
            "image_url": m_data["img"],
            "xp": xp_reward, "gold": gold_reward,
            "real_name": m_data["name"],
            "is_boss": is_boss,
            "level": final_lv
        })
        monster_id_counter += 1
            
    return monsters

class AttackWildSchema(BaseModel):
    monster_name: str
    is_dead: bool
    level: int 

@router.post("/wild/attack")
async def attack_wild(
    data: AttackWildSchema,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    msg = ""
    if data.is_dead:
        base_name = data.monster_name.split('(')[0].strip().replace(" 👑", "")
        monster_lv = data.level
        
        m_data = next((m for m in WILD_DB if m["name"] == base_name), None)
        
        # 🔥 計算獎勵 (與 get_wild 一致) 🔥
        base_min_lv = m_data["min_lv"] if m_data else 1
        is_boss = m_data.get("is_boss", False) if m_data else False
        
        base_bonus = base_min_lv * 3
        xp_gain = int(20 + base_bonus + monster_lv * 5)
        gold_gain = int(45 + base_bonus + monster_lv * 5)
        
        if is_boss:
            xp_gain *= 3
            gold_gain *= 3
            defeated = current_user.defeated_bosses.split(',') if current_user.defeated_bosses else []
            if base_name not in defeated:
                defeated.append(base_name)
                current_user.defeated_bosses = ",".join(defeated)
                msg += f" 🏆 擊敗首領 {base_name}！"

        current_user.exp += xp_gain
        current_user.pet_exp += xp_gain
        current_user.money += gold_gain
        
        msg = f"擊敗 {base_name}！獲得 {xp_gain} XP, {gold_gain} Gold" + msg
        
        if random.random() < 0.1:
            inventory = json.loads(current_user.inventory) if current_user.inventory else {}
            inventory["candy"] = inventory.get("candy", 0) + 1
            current_user.inventory = json.dumps(inventory)
            msg += " 🍬 獲得糖果！"

        lvl_msg = await check_levelup_dual(current_user)
        if lvl_msg: msg += f" 🎉 {lvl_msg}！"
            
        try:
            quests = json.loads(current_user.quests) if current_user.quests else []
            quest_updated = False
            for q in quests:
                if q["status"] == "ACTIVE" and q["target"] == base_name and monster_lv >= q["target_lv"]:
                    if q["now"] < q["req"]:
                        q["now"] += 1
                        quest_updated = True
                        if q["now"] >= q["req"]: q["status"] = "COMPLETED"; msg += " (任務完成!)"
            if quest_updated: current_user.quests = json.dumps(quests)
        except Exception as e: print(e)

        db.add(current_user)
        db.commit()
    
    return {"message": msg, "user": current_user}