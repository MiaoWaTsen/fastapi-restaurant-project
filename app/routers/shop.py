# app/routers/shop.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.common.websocket import manager 
import random

router = APIRouter()

# 扭蛋池 (你可以自己加更多神獸)
GACHA_POOL = [
    {"name": "皮卡丘", "atk": 25, "hp": 150, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg", "rate": 40},
    {"name": "耿鬼", "atk": 45, "hp": 120, "img": "https://img.pokemondb.net/artwork/large/gengar.jpg", "rate": 30},
    {"name": "快龍", "atk": 60, "hp": 300, "img": "https://img.pokemondb.net/artwork/large/dragonite.jpg", "rate": 20},
    {"name": "超夢", "atk": 120, "hp": 500, "img": "https://img.pokemondb.net/artwork/large/mewtwo.jpg", "rate": 5},
    {"name": "阿爾宙斯", "atk": 999, "hp": 999, "img": "https://img.pokemondb.net/artwork/large/arceus.jpg", "rate": 1},
]

@router.post("/gacha")
async def play_gacha(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cost = 200
    if current_user.money < cost:
        raise HTTPException(status_code=400, detail="金幣不足 (需要 200 G)")
    
    current_user.money -= cost
    
    # 簡單的抽獎邏輯 (純隨機，不看機率權重，想更專業可以加權重)
    prize = random.choice(GACHA_POOL)
    
    # 更新玩家外觀與數值 (保留等級，但更新基礎數值)
    current_user.pokemon_name = prize["name"]
    current_user.pokemon_image = prize["img"]
    # 這裡讓新數值加上等級加成，避免越抽越爛
    current_user.max_hp = prize["hp"] + (current_user.level * 10)
    current_user.hp = current_user.max_hp # 抽到新角補滿血
    current_user.attack = prize["atk"] + (current_user.level * 2)
    
    db.commit()
    
    msg = f"🎰 恭喜！勇者 [{current_user.username}] 抽到了 [{prize['name']}]！"
    await manager.broadcast(msg)
    
    return {"message": f"你獲得了 {prize['name']}！", "user": current_user}

@router.post("/heal")
async def buy_heal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cost = 50
    if current_user.money < cost: raise HTTPException(status_code=400, detail="金幣不足")
    
    current_user.money -= cost
    current_user.hp = current_user.max_hp
    db.commit()
    return {"message": "體力已補滿"}

# 🔥 PVP 攻擊玩家 🔥
@router.post("/pvp/{target_id}")
async def attack_player(
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target = db.query(User).filter(User.id == target_id).first()
    if not target: raise HTTPException(status_code=404, detail="找不到對手")
    if target.hp <= 0: raise HTTPException(status_code=400, detail="對手已經倒下了")
    if target.id == current_user.id: raise HTTPException(status_code=400, detail="不能打自己")

    # 傷害計算
    dmg = current_user.attack + random.randint(0, 5)
    target.hp = max(0, target.hp - dmg)
    
    # 獎勵
    current_user.exp += 20
    
    msg = f"⚔️ PVP戰報：[{current_user.username}] 攻擊了 [{target.username}]，造成 {dmg} 點傷害！"
    
    if target.hp == 0:
        win_money = int(target.money * 0.1) # 搶走對方 10% 的錢
        target.money -= win_money
        current_user.money += win_money
        msg += f" [{target.username}] 倒下了！[{current_user.username}] 搶走了 {win_money} G！"

    db.commit()
    await manager.broadcast(msg)
    
    return {"message": "攻擊成功"}