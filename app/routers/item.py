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

# --- 🌲 野怪資料 (數值已平衡調整) ---
# 為了達成「5回合擊殺」，基礎血量調整為原本 PDF 的 3 倍左右
WILD_DATA = [
    {"name": "皮卡丘", "base_hp": 240, "base_xp": 25, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"},
    {"name": "卡拉卡拉", "base_hp": 180, "base_xp": 25, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg"},
    {"name": "喵喵", "base_hp": 210, "base_xp": 25, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg"}
]

# 升級經驗表 (PDF source: 36-44)
LEVEL_XP = {
    1: 50, 2: 100, 3: 200, 4: 350, 5: 600, 
    6: 1000, 7: 1800, 8: 3000
}

def check_levelup(user: User):
    """檢查並執行升級 (PDF source: 45)"""
    required_xp = LEVEL_XP.get(user.level, 999999)
    if user.exp >= required_xp:
        user.level += 1
        user.exp -= required_xp
        # 升級獎勵: 最大血量*1.4, 攻擊力*1.5
        user.max_hp = int(user.max_hp * 1.4)
        user.hp = user.max_hp # 升級補滿
        user.attack = int(user.attack * 1.5)
        return True
    return False

# --- API ---

# 1. 取得野怪列表 (動態生成)
@router.get("/wild")
def get_wild_monsters(current_user: User = Depends(get_current_user)):
    monsters = []
    level = current_user.level
    
    # 數量規則：1 + level (PDF source: 4-5)
    count = 1 + level 
    
    monster_id_counter = 1
    
    for m_data in WILD_DATA:
        for i in range(count):
            # 🔥 平衡核心：野怪成長係數改為 1.5 🔥
            # 這樣才能跟上玩家攻擊力(1.5)的成長，維持永遠都要打 5 回合的難度
            scaling_factor = 1.5 ** (level - 1)
            
            hp = int(m_data["base_hp"] * scaling_factor)
            
            # 野怪攻擊力設計：
            # 讓野怪攻擊力約為玩家血量的 15% ~ 20%
            # 假設玩家血量成長是 1.4倍，野怪攻擊力成長設為 1.42倍
            base_player_hp = 200 # 參考值
            target_dmg = base_player_hp * 0.18 # 每次打玩家 36 點 (約6下死)
            attack = int(target_dmg * (1.42 ** (level - 1)))

            monsters.append({
                "id": monster_id_counter, 
                "name": f"{m_data['name']} (Lv.{level})",
                "hp": hp,
                "max_hp": hp,
                "attack": attack, 
                "image_url": m_data["img"],
                "base_xp": m_data["base_xp"], 
                "base_gold": m_data["base_gold"]
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
        base_xp = 25
        base_gold = 55
        lv = current_user.level
        
        # 獎勵公式 (PDF source: 6, 11, 16)
        xp_gain = base_xp + (lv * 5)
        gold_gain = base_gold + (lv * 5)
        
        current_user.exp += xp_gain
        current_user.money += gold_gain
        msg = f"擊敗 {data.monster_name}！獲得 {xp_gain} XP, {gold_gain} Gold"
        
        if check_levelup(current_user):
            msg += f" 🎉 升級了！(Lv.{current_user.level})"
            
        db.add(current_user)
        db.commit()
    
    return {"message": msg, "user": current_user}