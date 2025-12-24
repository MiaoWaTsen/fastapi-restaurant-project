# app/routers/social.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user
from app.common.websocket import manager

router = APIRouter()

#  建立官方帳號 (此函數可手動呼叫一次)
@router.post("/admin/create")
def create_admin(db: Session = Depends(get_db)):
    # 請在 main.py 啟動時或手動觸發
    # 帳密: admin / admin888
    # 這裡省略雜湊，實際應使用 auth.get_password_hash
    pass 

#  聊天發送
@router.post("/chat/send")
async def send_chat(content: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.is_muted: raise HTTPException(status_code=403, detail="你已被禁言")
    
    prefix = "🔴[官方]" if current_user.is_admin else f"[{current_user.username}]"
    msg = f"CHAT|{prefix}: {content}"
    await manager.broadcast(msg)
    return {"message": "sent"}

#  管理員指令
@router.post("/admin/action")
async def admin_action(action: str, target_id: int, content: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin: raise HTTPException(status_code=403, detail="權限不足")
    
    target = db.query(User).filter(User.id == target_id).first()
    
    if action == "mute":
        if target: target.is_muted = True; db.commit()
        return {"message": f"已禁言玩家 {target.username}"}
    elif action == "ban":
        if target: db.delete(target); db.commit()
        return {"message": "已移除玩家帳號"}
    elif action == "announce":
        await manager.broadcast(f"📢 [系統公告] {content}")
        return {"message": "公告已發送"}
    
    return {"message": "未知指令"}

#  每日簽到
DAILY_REWARDS = [300, 500, "candy:3", 1000, "growth:1", 2500, "golden:1"]

@router.post("/daily_checkin")
def daily_checkin(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = datetime.utcnow().date()
    if current_user.last_daily_claim == today:
        raise HTTPException(status_code=400, detail="今天已經簽到過了")
    
    # 連續登入判斷
    if current_user.last_daily_claim == today - timedelta(days=1):
        current_user.login_days = (current_user.login_days % 7) + 1
    else:
        current_user.login_days = 1
        
    reward = DAILY_REWARDS[current_user.login_days - 1]
    inv = json.loads(current_user.inventory)
    msg = ""
    
    if isinstance(reward, int):
        current_user.money += reward
        msg = f"獲得 {reward} Gold"
    else:
        type_, qty = reward.split(":")
        key = "candy" if type_ == "candy" else ("growth_candy" if type_ == "growth" else "golden_candy")
        inv[key] = inv.get(key, 0) + int(qty)
        msg = f"獲得 {key} x{qty}"
        
    current_user.inventory = json.dumps(inv)
    current_user.last_daily_claim = today
    db.commit()
    return {"message": f"Day {current_user.login_days} 簽到成功！{msg}", "user": current_user}

#  兌換碼
@router.post("/redeem")
def redeem_code(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 範例硬編碼
    if code == "POKEMON2025":
        current_user.money += 2000
        db.commit()
        return {"message": "兌換成功！獲得 2000 Gold"}
    raise HTTPException(status_code=400, detail="無效的序號")