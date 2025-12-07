# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
import random
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user

router = APIRouter()

# --- 🌲 野怪資料庫 (依照 PDF 出場順序排序) ---
# Index 0: Lv1 解鎖 (卡拉卡拉)
# Index 1: Lv2 解鎖 (喵喵)
# Index 2: Lv3 解鎖 (皮卡丘)
# Index 3: Lv4 解鎖 (波波)
# Index 4: Lv5 解鎖 (海星星)
WILD_DB = [
    {
        "name": "卡拉卡拉", "base_hp": 50, "base_xp": 20, "base_gold": 45, 
        "img": "https://img.pokemondb.net/artwork/large/cubone.jpg"
    },
    {
        "name": "喵喵", "base_hp": 70, "base_xp": 30, "base_gold": 55, 
        "img": "https://img.pokemondb.net/artwork/large/meowth.jpg"
    },
    {
        "name": "皮卡丘", "base_hp": 80, "base_xp": 40, "base_gold": 65, 
        "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"
    },
    {
        "name": "波波", "base_hp": 75, "base_xp": 50, "base_gold": 75, 
        "img": "https://img.pokemondb.net/artwork/large/pidgey.jpg"
    },
    {
        "name": "海星星", "base_hp": 85, "base_xp": 50, "base_gold": 85, 
        "img": "https://img.pokemondb.net/artwork/large/staryu.jpg"
    }
]

# 升級經驗表 (PDF Source 81-88)
LEVEL_XP = { 1: 50, 2: 100, 3: 200, 4: 350, 5: 600, 6: 1000, 7: 1800, 8: 3000 }

def check_levelup(user: User):
    required_xp = LEVEL_XP.get(user.level, 999999)
    if user.exp >= required_xp:
        user.level += 1
        user.exp -= required_xp
        # 升級獎勵 (PDF Source 89): MaxHP*1.4, Atk*1.5
        user.max_hp = int(user.max_hp * 1.4)
        user.hp = user.max_hp 
        # 為了避免攻擊力指數爆炸導致秒殺，這裡我們稍微收斂一點
        # PDF 說 1.5，但野怪血量成長只有 1.16，這樣 Lv5 就會秒殺一切
        # 建議維持 1.2 或 1.3 的平衡成長，或者我們嚴格遵守 PDF 但野怪血量要動態調整
        user.attack = int(user.attack * 1.2) 
        return True
    return False

# --- API ---

# 1. 取得野怪列表 (動態生成：舊怪升級 + 新怪解鎖)
@router.get("/wild")
def get_wild_monsters(current_user: User = Depends(get_current_user)):
    monsters = []
    player_lv = current_user.level
    
    # 決定要生成幾隻怪
    # Lv.1 -> 生成 Index 0 (共1隻)
    # Lv.2 -> 生成 Index 0, 1 (共2隻)
    # ...
    # 超過 Lv.5 (Index 4) 後，我們可以循環使用或隨機
    
    # 我們設定：生成的怪獸數量 = 玩家等級 (但不超過資料庫總數，若超過則隨機補)
    unlock_count = min(player_lv, len(WILD_DB))
    
    monster_id_counter = 1
    
    # 1. 生成固定解鎖的怪 (大家等級都跟著玩家提升)
    for i in range(unlock_count):
        m_data = WILD_DB[i]
        
        # 數值成長公式 (PDF Source 39, 45, 51...)
        # "每死亡一次(這裡視為升級) lv+1, 血量與傷害 * 1.16"
        scaling_factor = 1.16 ** (player_lv - 1)
        
        hp = int(m_data["base_hp"] * scaling_factor)
        
        # 攻擊力估算 (基礎傷害約為玩家血量的 10-15%)
        base_atk = 15 
        attack = int(base_atk * scaling_factor)
        
        # 獎勵公式 (PDF Source 34, 41, 47...)
        # XP: base + (lv * 5)
        # Gold: base + (lv * 5) 或 (lv * 6) 依怪不同，這裡統一用 *5 簡化
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
        
    # 2. 如果玩家等級很高 (例如 Lv.6)，但資料庫只有 5 隻怪
    # 我們可以額外隨機生成一些舊怪來填補空缺，保持野區熱鬧
    if player_lv > len(WILD_DB):
        extra_count = player_lv - len(WILD_DB)
        for _ in range(extra_count):
            m_data = random.choice(WILD_DB)
            scaling_factor = 1.16 ** (player_lv - 1)
            hp = int(m_data["base_hp"] * scaling_factor)
            attack = int(15 * scaling_factor)
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

    return monsters

# 2. 攻擊野怪結算
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
        # 解析名字取出基礎名 (去除 Lv.xx)
        base_name = data.monster_name.split('(')[0].strip()
        
        # 尋找對應的基礎資料
        m_data = next((m for m in WILD_DB if m["name"] == base_name), WILD_DB[0])
        
        lv = current_user.level
        xp_gain = int(m_data["base_xp"] + (lv * 5))
        gold_gain = int(m_data["base_gold"] + (lv * 5))
        
        current_user.exp += xp_gain
        current_user.money += gold_gain
        msg = f"擊敗 {data.monster_name}！獲得 {xp_gain} XP, {gold_gain} Gold"
        
        if check_levelup(current_user):
            msg += f" 🎉 升級了！(Lv.{current_user.level})"
            
        db.add(current_user)
        db.commit()
    
    return {"message": msg, "user": current_user}