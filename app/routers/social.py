# app/routers/social.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import uuid #

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user
from app.common.websocket import manager
from app.core.security import get_password_hash
# 🔥 這裡不需要引入 shop.py，避免循環引用，我們直接在下面生成資料 🔥

router = APIRouter()

# (... 前面的 admin/init, leaderboard, chat, admin action, daily checkin 保持不變 ...)
# 請保留原有的程式碼，只替換 redeem_code 部分

TOTAL_POKEMON_COUNT = 21

@router.get("/admin/init")
def init_admin(db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == "admin").first()
    if existing: return {"message": "管理員已存在！帳號: admin / 密碼: admin888"}
    admin_user = User(username="admin", hashed_password=get_password_hash("admin888"), is_admin=True, level=99, money=99999999, pokemon_storage="[]", inventory="{}")
    db.add(admin_user); db.commit()
    return {"message": "✅ 管理員建立成功！帳號: admin / 密碼: admin888"}

@router.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    leaders = db.query(User).order_by(desc(User.level), desc(User.money)).limit(10).all()
    result = []
    for idx, u in enumerate(leaders):
        unlocked_count = len(u.unlocked_monsters.split(',')) if u.unlocked_monsters else 0
        collection_rate = int((unlocked_count / TOTAL_POKEMON_COUNT) * 100)
        name_display = f"🔴 {u.username}" if u.is_admin else u.username
        result.append({"rank": idx + 1, "username": name_display, "level": u.level, "money": u.money, "pet": u.pokemon_name, "img": u.pokemon_image, "collection": collection_rate})
    return result

@router.post("/chat/send")
async def send_chat(content: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.is_muted: raise HTTPException(status_code=403, detail="你已被禁言")
    prefix = "🔴[官方]" if current_user.is_admin else f"[{current_user.username}]"
    msg = f"CHAT|{prefix}: {content}"
    await manager.broadcast(msg)
    return {"message": "sent"}

@router.post("/admin/action")
async def admin_action(action: str, target_id: str, content: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin: raise HTTPException(status_code=403, detail="權限不足")
    try: tid = int(target_id); target = db.query(User).filter(User.id == tid).first()
    except: target = None
    if action == "mute":
        if target: target.is_muted = True; db.commit(); return {"message": f"已禁言玩家 {target.username}"}
        return {"message": "找不到玩家ID"}
    elif action == "ban":
        if target: 
            if target.is_admin: return {"message": "不能刪除管理員"}
            db.delete(target); db.commit(); return {"message": f"已移除玩家 {target.username}"}
        return {"message": "找不到玩家ID"}
    elif action == "announce":
        await manager.broadcast(f"📢 [系統公告] {content}"); return {"message": "公告已發送"}
    return {"message": "未知指令"}

DAILY_REWARDS = [300, 500, "candy:3", 1000, "growth:1", 2500, "golden:1"]
@router.post("/daily_checkin")
def daily_checkin(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = datetime.utcnow().date()
    if current_user.last_daily_claim == today: raise HTTPException(status_code=400, detail="今天已經簽到過了")
    if current_user.last_daily_claim == today - timedelta(days=1): current_user.login_days = (current_user.login_days % 7) + 1
    else: current_user.login_days = 1
    reward = DAILY_REWARDS[current_user.login_days - 1]
    inv = json.loads(current_user.inventory)
    msg = ""
    if isinstance(reward, int): current_user.money += reward; msg = f"獲得 {reward} Gold"
    else:
        type_, qty = reward.split(":")
        key = "candy" if type_ == "candy" else ("growth_candy" if type_ == "growth" else "golden_candy")
        inv[key] = inv.get(key, 0) + int(qty)
        msg = f"獲得 {key} x{qty}"
    current_user.inventory = json.dumps(inv)
    current_user.last_daily_claim = today
    db.commit()
    return {"message": f"Day {current_user.login_days} 簽到成功！{msg}", "user": current_user}

# 🔥 🔥 更新：補償兌換碼邏輯 🔥 🔥
@router.post("/redeem")
def redeem_code(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = json.loads(current_user.inventory)
    msg = ""
    
    # 檢查是否已領過 (這裡簡化，實務上應記錄已領取過的 Code)
    # 為了方便測試，暫不限制領取次數，或者您可以自行添加 used_codes 欄位
    
    if code == "compensation_gold":
        current_user.money += 30000
        msg = "補償領取：30000 Gold"
        
    elif code == "compensation_candy":
        inv["candy"] = inv.get("candy", 0) + 30
        msg = "補償領取：30 顆神奇糖果"
        
    elif code == "compensation_goldencandy":
        inv["golden_candy"] = inv.get("golden_candy", 0) + 5
        msg = "補償領取：5 顆黃金糖果"
        
    elif code == "conmoenstion_snorlax": # 配合您的拼寫
        box = json.loads(current_user.pokemon_storage)
        if len(box) >= 25: raise HTTPException(status_code=400, detail="盒子已滿，無法領取寶可夢")
        
        # 建立 IV 80 的卡比獸
        snorlax = {
            "uid": str(uuid.uuid4()),
            "name": "卡比獸",
            "iv": 80,
            "lv": 1,
            "exp": 0
        }
        box.append(snorlax)
        current_user.pokemon_storage = json.dumps(box)
        
        # 解鎖圖鑑
        unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
        if "卡比獸" not in unlocked:
            unlocked.append("卡比獸")
            current_user.unlocked_monsters = ",".join(unlocked)
            
        msg = "補償領取：IV 80 卡比獸！"
        
    else:
        raise HTTPException(status_code=400, detail="無效的序號")
        
    current_user.inventory = json.dumps(inv)
    db.commit()
    return {"message": msg}