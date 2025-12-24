# app/routers/social.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from datetime import datetime, timedelta
import json
import random

from app.db.session import get_db
from app.models.user import User
from app.models.friend import Friend
from app.models.gift import Gift, GiftCooldown
from app.common.deps import get_current_user
from app.common.websocket import manager
from app.core.security import get_password_hash # 🔥 新增引入

router = APIRouter()

# 總寶可夢數量 21
TOTAL_POKEMON_COUNT = 21

# 🔥 新增：一鍵建立管理員 (admin/admin888)  🔥
@router.get("/admin/init")
def init_admin(db: Session = Depends(get_db)):
    # 檢查是否已存在
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        return {"message": "管理員已存在！帳號: admin / 密碼: admin888"}
    
    # 建立官方帳號
    admin_user = User(
        username="admin",
        hashed_password=get_password_hash("admin888"),
        is_admin=True,
        level=99,          # 官方等級
        money=99999999,    # 官方經費
        pokemon_storage="[]",
        inventory="{}"
    )
    db.add(admin_user)
    db.commit()
    return {"message": "✅ 管理員建立成功！帳號: admin / 密碼: admin888"}

# --- 🏆 排行榜 ---
@router.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    leaders = db.query(User).order_by(desc(User.level), desc(User.money)).limit(10).all()
    result = []
    for idx, u in enumerate(leaders):
        unlocked_count = len(u.unlocked_monsters.split(',')) if u.unlocked_monsters else 0
        collection_rate = int((unlocked_count / TOTAL_POKEMON_COUNT) * 100)
        
        # 管理員標記
        name_display = f"🔴 {u.username}" if u.is_admin else u.username
        
        result.append({
            "rank": idx + 1,
            "username": name_display,
            "level": u.level,
            "money": u.money,
            "pet": u.pokemon_name,
            "img": u.pokemon_image,
            "collection": collection_rate 
        })
    return result

# --- 聊天室 ---
@router.post("/chat/send")
async def send_chat(content: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.is_muted: raise HTTPException(status_code=403, detail="你已被禁言")
    
    # 官方帳號有特殊前綴 [cite: 247]
    prefix = "🔴[官方]" if current_user.is_admin else f"[{current_user.username}]"
    msg = f"CHAT|{prefix}: {content}"
    await manager.broadcast(msg)
    return {"message": "sent"}

# --- 管理員指令  ---
@router.post("/admin/action")
async def admin_action(action: str, target_id: str, content: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin: raise HTTPException(status_code=403, detail="權限不足")
    
    # target_id 可能是字串，嘗試轉換
    try:
        tid = int(target_id)
        target = db.query(User).filter(User.id == tid).first()
    except:
        target = None

    if action == "mute":
        if target: 
            target.is_muted = True
            db.commit()
            return {"message": f"已禁言玩家 {target.username}"}
        return {"message": "找不到玩家ID"}
        
    elif action == "ban":
        if target: 
            if target.is_admin: return {"message": "不能刪除管理員"}
            db.delete(target)
            db.commit()
            return {"message": f"已移除玩家 {target.username}"}
        return {"message": "找不到玩家ID"}
        
    elif action == "announce":
        await manager.broadcast(f"📢 [系統公告] {content}")
        return {"message": "公告已發送"}
    
    return {"message": "未知指令"}

# --- 每日簽到 [cite: 257-264] ---
DAILY_REWARDS = [300, 500, "candy:3", 1000, "growth:1", 2500, "golden:1"]

@router.post("/daily_checkin")
def daily_checkin(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = datetime.utcnow().date()
    if current_user.last_daily_claim == today:
        raise HTTPException(status_code=400, detail="今天已經簽到過了")
    
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

# --- 兌換碼 ---
@router.post("/redeem")
def redeem_code(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if code == "POKEMON2025":
        current_user.money += 2000
        db.commit()
        return {"message": "兌換成功！獲得 2000 Gold"}
    raise HTTPException(status_code=400, detail="無效的序號")

# --- 好友與禮物 (保持原有邏輯) ---
@router.get("/list")
def get_friends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    friends_rel = db.query(Friend).filter(or_(Friend.user_id == current_user.id, Friend.friend_id == current_user.id),Friend.status == "ACCEPTED").all()
    friend_ids = []
    for f in friends_rel: friend_ids.append(f.friend_id if f.user_id == current_user.id else f.user_id)
    if not friend_ids: return []
    friends = db.query(User).filter(User.id.in_(friend_ids)).all()
    today = datetime.utcnow().date()
    result = []
    for f in friends:
        cooldown = db.query(GiftCooldown).filter(GiftCooldown.sender_id == current_user.id, GiftCooldown.receiver_id == f.id, GiftCooldown.last_sent_date == today).first()
        result.append({"id": f.id, "username": f.username, "level": f.level, "pet": f.pokemon_name, "img": f.pokemon_image, "can_gift": (cooldown is None)})
    return result

@router.get("/requests")
def get_friend_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reqs = db.query(Friend).filter(Friend.friend_id == current_user.id, Friend.status == "PENDING").all()
    results = []
    for r in reqs:
        sender = db.query(User).filter(User.id == r.user_id).first()
        if sender: results.append({"req_id": r.id, "sender_name": sender.username, "sender_lv": sender.level})
    return results

@router.post("/add/{target_id}")
def send_request(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if target_id == current_user.id: raise HTTPException(status_code=400, detail="不能加自己")
    existing = db.query(Friend).filter(or_(and_(Friend.user_id == current_user.id, Friend.friend_id == target_id),and_(Friend.user_id == target_id, Friend.friend_id == current_user.id))).first()
    if existing: return {"message": "已經是好友了" if existing.status == "ACCEPTED" else "請求已發送或待處理"}
    new_req = Friend(user_id=current_user.id, friend_id=target_id, status="PENDING")
    db.add(new_req); db.commit()
    return {"message": "好友邀請已發送"}

@router.post("/accept/{req_id}")
def accept_request(req_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(Friend).filter(Friend.id == req_id, Friend.friend_id == current_user.id).first()
    if not req: raise HTTPException(status_code=404, detail="找不到請求")
    req.status = "ACCEPTED"; db.commit()
    return {"message": "已成為好友！"}

@router.post("/reject/{req_id}")
def reject_request(req_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(Friend).filter(Friend.id == req_id, Friend.friend_id == current_user.id).first()
    if req: db.delete(req); db.commit()
    return {"message": "已拒絕"}

@router.get("/gifts")
def get_my_gifts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    gifts = db.query(Gift).filter(Gift.receiver_id == current_user.id).all()
    return [{"id": g.id, "sender": g.sender_name} for g in gifts]

@router.post("/gift/send/{friend_id}")
def send_gift(friend_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    is_friend = db.query(Friend).filter(or_(and_(Friend.user_id == current_user.id, Friend.friend_id == friend_id),and_(Friend.user_id == friend_id, Friend.friend_id == current_user.id)),Friend.status == "ACCEPTED").first()
    if not is_friend: raise HTTPException(status_code=400, detail="非好友關係")
    today = datetime.utcnow().date()
    cooldown = db.query(GiftCooldown).filter(GiftCooldown.sender_id == current_user.id, GiftCooldown.receiver_id == friend_id, GiftCooldown.last_sent_date == today).first()
    if cooldown: raise HTTPException(status_code=400, detail="今天已經送過該好友禮物了")
    new_gift = Gift(sender_id=current_user.id, receiver_id=friend_id, sender_name=current_user.username)
    db.add(new_gift)
    new_cd = GiftCooldown(sender_id=current_user.id, receiver_id=friend_id, last_sent_date=today)
    db.add(new_cd)
    db.commit()
    return {"message": "禮物已發送！"}

@router.post("/gift/open/{gift_id}")
def open_gift(gift_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    gift = db.query(Gift).filter(Gift.id == gift_id, Gift.receiver_id == current_user.id).first()
    if not gift: raise HTTPException(status_code=404, detail="禮物不存在")
    amount = random.randint(300, 1500)
    current_user.money += amount
    db.delete(gift)
    db.commit()
    return {"message": f"獲得 {amount} 金幣！", "amount": amount, "user": current_user}