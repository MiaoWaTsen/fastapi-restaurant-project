# app/routers/shop.py

from fastapi import APIRouter, Depends, HTTPException
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.common.deps import get_current_user
from app.models.user import User, UserRead
from app.common.websocket import manager 

router = APIRouter()

# 定義商品列表 (由後端控制價格與效果，避免作弊)
SHOP_ITEMS = {
    "potion": {
        "name": "大補藥 💊",
        "price": 50,
        "description": "回復 50 點生命值",
        "effect": "heal",
        "value": 50
    },
    "str_potion": {
        "name": "力量藥劑 ⚔️",
        "price": 200,
        "description": "永久增加 5 點攻擊力",
        "effect": "buff_atk",
        "value": 5
    },
    "life_gem": {
        "name": "生命寶石 💎",
        "price": 500,
        "description": "永久增加 50 點生命上限",
        "effect": "buff_max_hp",
        "value": 50
    }
}

@router.get("/list")
def get_shop_items():
    """回傳商品列表給前端顯示"""
    return SHOP_ITEMS

@router.post("/buy/{item_id}", response_model=UserRead)
async def buy_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. 檢查商品是否存在
    item = SHOP_ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 2. 檢查錢夠不夠
    if current_user.money < item["price"]:
        raise HTTPException(status_code=400, detail="金幣不足！快去打怪賺錢！")

    # 3. 扣錢
    current_user.money -= item["price"]

    # 4. 應用效果
    effect = item["effect"]
    value = item["value"]
    
    msg = ""

    if effect == "heal":
        # 補血 (不能超過上限)
        old_hp = current_user.hp
        current_user.hp = min(current_user.max_hp, current_user.hp + value)
        heal_amount = current_user.hp - old_hp
        msg = f"使用了 [{item['name']}]，回復了 {heal_amount} 點生命！"

    elif effect == "buff_atk":
        # 加攻擊
        current_user.attack += value
        msg = f"喝下了 [{item['name']}]，攻擊力提升了 {value} 點！(目前: {current_user.attack})"

    elif effect == "buff_max_hp":
        # 加血量上限 (順便補滿血)
        current_user.max_hp += value
        current_user.hp += value
        msg = f"裝備了 [{item['name']}]，生命上限提升了 {value} 點！"

    # 5. 存檔與廣播
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    # 廣播給所有人看 (炫耀消費)
    await manager.broadcast(f"💰 勇者 [{current_user.username}] {msg}")

    return current_user