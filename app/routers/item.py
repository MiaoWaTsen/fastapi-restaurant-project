# app/routers/item.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
import random

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user
# 為了避免循環匯入，我們在這裡簡單重寫升級邏輯，或者從 auth 匯入
# 假設 auth.py 裡有 check_levelup，這裡為了獨立性，我直接寫在下面

router = APIRouter()

# --- 🌲 野怪資料 (PDF source: 6-20) ---
WILD_DATA = [
    {"name": "皮卡丘", "base_hp": 80, "base_xp": 25, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"},
    {"name": "卡拉卡拉", "base_hp": 50, "base_xp": 25, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg"},
    {"name": "喵喵", "base_hp": 70, "base_xp": 25, "base_gold": 55, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg"}
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
        # 升級獎勵: 最大血量*1.4 (四雪五入取整), 攻擊力*1.5
        user.max_hp = int(user.max_hp * 1.4)
        user.hp = user.max_hp # 升級補滿
        user.attack = int(user.attack * 1.5)
        return True
    return False

# --- API ---

# 1. 取得野怪列表 (動態生成，不存資料庫)
@router.get("/wild")
def get_wild_monsters(current_user: User = Depends(get_current_user)):
    monsters = []
    level = current_user.level
    
    # 規則：每種怪各生成 1 + (level-1) 隻 -> 其實就是 level 隻 (PDF source: 4-5)
    # PDF 說初始各2隻，之後每升1級各多1隻 => 數量 = 1 + level
    count = 1 + level 
    
    monster_id_counter = 1
    
    for m_data in WILD_DATA:
        for i in range(count):
            # 野怪強度隨等級上升 (PDF source: 3)
            # 這裡假設野怪等級跟隨玩家等級，係數設為 1.1
            hp = int(m_data["base_hp"] * (1.1 ** (level-1)))
            
            monsters.append({
                "id": monster_id_counter, # 這是臨時ID，只給前端識別用
                "name": f"{m_data['name']} (Lv.{level})",
                "hp": hp,
                "max_hp": hp,
                "attack": int(5 * (1.1 ** (level-1))), # 基礎攻擊力估算
                "image_url": m_data["img"],
                # 這裡把獎勵基礎值傳給前端參考，但實際結算在後端
                "base_xp": m_data["base_xp"], 
                "base_gold": m_data["base_gold"]
            })
            monster_id_counter += 1
            
    return monsters

# 2. 攻擊野怪結算
class AttackWildSchema(BaseModel):
    monster_name: str # 用名字來判斷是哪種怪
    is_dead: bool

@router.post("/wild/attack")
async def attack_wild(
    data: AttackWildSchema,
    db: Session = Depends(get_db), # 這裡要用 db 來存 User 的變更
    current_user: User = Depends(get_current_user)
):
    msg = ""
    
    # 如果野怪死了，計算獎勵
    if data.is_dead:
        # 根據名字判斷基礎數值 (簡單 parse)
        base_xp = 25
        base_gold = 55
        
        # PDF 公式: 25 + (lv * 5) 
        # 这里的 lv 指的是野怪等級，也就是玩家等級
        lv = current_user.level
        
        xp_gain = base_xp + (lv * 5)
        gold_gain = base_gold + (lv * 5)
        
        current_user.exp += xp_gain
        current_user.money += gold_gain
        msg = f"擊敗 {data.monster_name}！獲得 {xp_gain} XP, {gold_gain} Gold"
        
        # 檢查升級
        if check_levelup(current_user):
            msg += f" 🎉 升級了！(Lv.{current_user.level})"
            
        db.add(current_user)
        db.commit()
    
    return {"message": msg, "user": current_user}