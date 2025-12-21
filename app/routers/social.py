# app/routers/social.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from datetime import datetime
import random

from app.db.session import get_db
from app.models.user import User
from app.models.friend import Friend
from app.models.gift import Gift, GiftCooldown
from app.common.deps import get_current_user

router = APIRouter()

# --- 🏆 排行榜系統 (新增) ---
@router.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    # 依照 等級(高到低) -> 金幣(高到低) 排序，取前 10 名
    leaders = db.query(User).order_by(desc(User.level), desc(User.money)).limit(10).all()
    
    result = []
    for idx, u in enumerate(leaders):
        # 計算收集率給前端顯示
        unlocked_count = len(u.unlocked_monsters.split(',')) if u.unlocked_monsters else 0
        result.append({
            "rank": idx + 1,
            "username": u.username,
            "level": u.level,
            "money": u.money,
            "pet": u.pokemon_name,
            "img": u.pokemon_image,
            "collection": unlocked_count
        })
    return result

# --- 好友基本功能 (保持不變) ---

@router.get("/list")
def get_friends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    friends_rel = db.query(Friend).filter(
        or_(Friend.user_id == current_user.id, Friend.friend_id == current_user.id),
        Friend.status == "ACCEPTED"
    ).all()
    
    friend_ids = []
    for f in friends_rel:
        if f.user_id == current_user.id: friend_ids.append(f.friend_id)
        else: friend_ids.append(f.user_id)
        
    if not friend_ids: return []
    
    friends = db.query(User).filter(User.id.in_(friend_ids)).all()
    
    today = datetime.utcnow().date()
    result = []
    for f in friends:
        cooldown = db.query(GiftCooldown).filter(
            GiftCooldown.sender_id == current_user.id,
            GiftCooldown.receiver_id == f.id,
            GiftCooldown.last_sent_date == today
        ).first()
        
        result.append({
            "id": f.id, 
            "username": f.username, 
            "level": f.level, 
            "pet": f.pokemon_name, 
            "img": f.pokemon_image,
            "can_gift": (cooldown is None)
        })
        
    return result

@router.get("/requests")
def get_friend_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reqs = db.query(Friend).filter(
        Friend.friend_id == current_user.id,
        Friend.status == "PENDING"
    ).all()
    
    results = []
    for r in reqs:
        sender = db.query(User).filter(User.id == r.user_id).first()
        if sender:
            results.append({"req_id": r.id, "sender_name": sender.username, "sender_lv": sender.level})
    return results

@router.post("/add/{target_id}")
def send_request(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if target_id == current_user.id: raise HTTPException(status_code=400, detail="不能加自己")
    
    existing = db.query(Friend).filter(
        or_(
            and_(Friend.user_id == current_user.id, Friend.friend_id == target_id),
            and_(Friend.user_id == target_id, Friend.friend_id == current_user.id)
        )
    ).first()
    
    if existing:
        if existing.status == "ACCEPTED": return {"message": "已經是好友了"}
        return {"message": "請求已發送或待處理"}
    
    new_req = Friend(user_id=current_user.id, friend_id=target_id, status="PENDING")
    db.add(new_req)
    db.commit()
    return {"message": "好友邀請已發送"}

@router.post("/accept/{req_id}")
def accept_request(req_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(Friend).filter(Friend.id == req_id, Friend.friend_id == current_user.id).first()
    if not req: raise HTTPException(status_code=404, detail="找不到請求")
    req.status = "ACCEPTED"
    db.commit()
    return {"message": "已成為好友！"}

@router.post("/reject/{req_id}")
def reject_request(req_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(Friend).filter(Friend.id == req_id, Friend.friend_id == current_user.id).first()
    if req:
        db.delete(req)
        db.commit()
    return {"message": "已拒絕"}

# --- 禮物系統 ---

@router.get("/gifts")
def get_my_gifts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    gifts = db.query(Gift).filter(Gift.receiver_id == current_user.id).all()
    return [{"id": g.id, "sender": g.sender_name} for g in gifts]

@router.post("/gift/send/{friend_id}")
def send_gift(friend_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    is_friend = db.query(Friend).filter(
        or_(
            and_(Friend.user_id == current_user.id, Friend.friend_id == friend_id),
            and_(Friend.user_id == friend_id, Friend.friend_id == current_user.id)
        ),
        Friend.status == "ACCEPTED"
    ).first()
    
    if not is_friend: raise HTTPException(status_code=400, detail="非好友關係")

    today = datetime.utcnow().date()
    cooldown = db.query(GiftCooldown).filter(
        GiftCooldown.sender_id == current_user.id,
        GiftCooldown.receiver_id == friend_id,
        GiftCooldown.last_sent_date == today
    ).first()
    
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