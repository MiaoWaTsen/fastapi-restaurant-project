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

# --- 🌲 野怪資料 ---
WILD_DATA = [
    {"name": "皮卡丘", "base_hp": 160, "base_xp": 25, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"},
    {"name": "卡拉卡拉", "base_hp": 100, "base_xp": 25, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg"},
    {"name": "喵喵", "base_hp": 140, "base_xp": 25, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg"}
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

# 1. 取得野怪列表 (動態生成)
@router.get("/wild")
def get_wild_monsters(current_user: User = Depends(get_current_user)):
    monsters = []
    level = current_user.level
    count = 1 + level 
    monster_id_counter = 1
    
    for m_data in WILD_DATA:
        for i in range(count):
            scaling_factor = 1.25 ** (level - 1)
            hp = int(m_data["base_hp"] * scaling_factor)
            
            # 🔥 平衡修正：提升野怪攻擊力 (0.12 -> 0.16) 🔥
            base_player_hp = 200 
            target_dmg = base_player_hp * 0.16 # 稍微調痛一點
            attack = int(target_dmg * scaling_factor)

            # 🔥 計算顯示用的 XP 和 Gold (讓前端顯示正確數值) 🔥
            # 公式: base + (lv * 5)
            real_xp = m_data["base_xp"] + (level * 5)
            real_gold = m_data["base_gold"] + (level * 5)

            monsters.append({
                "id": monster_id_counter, 
                "name": f"{m_data['name']} (Lv.{level})",
                "hp": hp,
                "max_hp": hp,
                "attack": attack, 
                "image_url": m_data["img"],
                "xp_yield": real_xp,   # 傳送真實 XP
                "gold_yield": real_gold # 傳送真實 Gold
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
        # 基礎值 (假設所有怪基礎值相同簡化計算，或可依名字判斷)
        base_xp = 25
        base_gold = 55
        lv = current_user.level
        
        # 獎勵公式: 25 + (lv * 5)
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