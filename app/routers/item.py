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

# --- 🌲 野怪資料 (PDF Source 125-139) ---
# 依照出場等級排序
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
    
    def get_req_xp(lv):
        if lv < 10: return LEVEL_XP.get(lv, 3000)
        return 3000 + (lv - 10) * 1000

    # 1. 訓練師升級
    req_xp_player = get_req_xp(user.level)
    if user.exp >= req_xp_player:
        user.level += 1
        user.exp -= req_xp_player
        msg_list.append(f"訓練師升級(Lv.{user.level})")
        # 🔥 全頻廣播 🔥
        await manager.broadcast(f"📢 恭喜玩家 [{user.username}] 提升到了 訓練師等級 {user.level}！")
        
    # 2. 寶可夢升級
    if user.pet_level < user.level or (user.level == 1 and user.pet_level == 1):
        req_xp_pet = get_req_xp(user.pet_level)
        while user.pet_exp >= req_xp_pet:
            if user.pet_level >= user.level and user.level > 1: break # 受限於訓練師等級
            user.pet_level += 1
            user.pet_exp -= req_xp_pet
            
            # 升級數值成長 -> Atk*1.12, HP*1.06
            user.max_hp = int(user.max_hp * 1.06)
            user.hp = user.max_hp
            user.attack = int(user.attack * 1.12)
            
            msg_list.append(f"{user.pokemon_name}升級(Lv.{user.pet_level})")
            req_xp_pet = get_req_xp(user.pet_level)
            
    return " & ".join(msg_list) if msg_list else None

# 1. 取得野怪 (根據等級過濾)
@router.get("/wild")
def get_wild_monsters(
    level: int = Query(None), 
    current_user: User = Depends(get_current_user)
):
    monsters = []
    # 預設顯示玩家當前等級能遇到的所有怪
    player_lv = current_user.level
    
    # 找出所有符合條件的怪 (min_lv <= player_lv)
    # 如果指定了 level，則只回傳該等級的怪 (用於任務或刷特定怪)
    target_lv = level if level else player_lv
    if target_lv > player_lv: target_lv = player_lv # 防呆
    
    available_monsters = [m for m in WILD_DB if m["min_lv"] <= target_lv]
    
    # 如果指定了特定等級，只顯示那一隻 (例如指定 Lv2 就只出波波)
    if level:
        # 找最接近該等級的怪
        specific_monster = next((m for m in reversed(WILD_DB) if m["min_lv"] <= level), WILD_DB[0])
        available_monsters = [specific_monster]

    monster_id_counter = 1
    for m_data in available_monsters:
        # 計算野怪等級：它出場的等級
        m_lv = m_data["min_lv"]
        # 如果玩家選了比較高的等級來打這隻怪，怪也要升級
        # 但為了符合 PDF 描述「升上Lv2時新增Lv2喵喵，卡拉卡拉升上2級」
        # 所以怪物的等級 = 玩家選擇的等級 (target_lv)
        
        # 成長公式: 1.12^(lv-1) for atk, 1.06^(lv-1) for hp
        # 基準是以怪物的 base_lv 為 1 還是以 target_lv 為 1? 
        # PDF 說「每死亡一次lv+1...效果不改變」，暗示野怪是動態成長的
        
        hp_scale = 1.06 ** (target_lv - 1)
        atk_scale = 1.12 ** (target_lv - 1)
        
        hp = int(m_data["base_hp"] * hp_scale)
        attack = int(m_data["base_atk"] * atk_scale)
        
        # 獎勵公式 (假設)
        xp_reward = int(20 + target_lv * 5)
        gold_reward = int(45 + target_lv * 5)

        monsters.append({
            "id": monster_id_counter,
            "name": f"{m_data['name']} (Lv.{target_lv})",
            "hp": hp, "max_hp": hp, "attack": attack,
            "image_url": m_data["img"],
            "xp": xp_reward, "gold": gold_reward,
            "real_name": m_data["name"] # 用於任務比對
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
        base_name = data.monster_name.split('(')[0].strip()
        monster_lv = data.level
        
        xp_gain = int(20 + monster_lv * 5)
        gold_gain = int(45 + monster_lv * 5)
        
        current_user.exp += xp_gain
        current_user.pet_exp += xp_gain
        current_user.money += gold_gain
        
        msg = f"擊敗 {data.monster_name}！獲得 {xp_gain} XP, {gold_gain} Gold"
        
        # 🔥 掉落系統：10% 機率掉糖果 🔥
        if random.random() < 0.1:
            inventory = json.loads(current_user.inventory) if current_user.inventory else {}
            inventory["candy"] = inventory.get("candy", 0) + 1
            current_user.inventory = json.dumps(inventory)
            msg += " 🍬 獲得了神奇糖果！"

        # 升級檢查
        lvl_msg = await check_levelup_dual(current_user)
        if lvl_msg: msg += f" 🎉 {lvl_msg}！"
            
        # 任務進度更新 (需比對名字和等級)
        try:
            quests = json.loads(current_user.quests) if current_user.quests else []
            quest_updated = False
            for q in quests:
                # 判斷名字符合 且 等級符合 (target_lv)
                if q["status"] == "ACTIVE" and q["target"] == base_name and q["target_lv"] == monster_lv:
                    if q["now"] < q["req"]:
                        q["now"] += 1
                        quest_updated = True
                        if q["now"] >= q["req"]: q["status"] = "COMPLETED"; msg += " (任務完成!)"
            if quest_updated: current_user.quests = json.dumps(quests)
        except Exception as e: print(e)

        db.add(current_user)
        db.commit()
    
    return {"message": msg, "user": current_user}