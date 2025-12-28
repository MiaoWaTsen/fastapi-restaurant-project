# app/routers/social.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import json
from datetime import datetime

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
# 🔥 改為引入 Friendship 🔥
from app.models.friendship import Friendship 

router = APIRouter()

@router.get("/list")
def get_friend_list(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 查詢所有 is_accepted = True 的紀錄
    # 邏輯：我是申請者 (requester) 或者 我是接收者 (accepter)
    friends_rel = db.query(Friendship).filter(
        or_(Friendship.requester_id == current_user.id, Friendship.accepter_id == current_user.id),
        Friendship.is_accepted == True
    ).all()
    
    result = []
    for rel in friends_rel:
        # 判斷誰是對方
        target_id = rel.accepter_id if rel.requester_id == current_user.id else rel.requester_id
        target_user = db.query(User).filter(User.id == target_id).first()
        
        if target_user:
            can_gift = True 
            result.append({
                "id": target_user.id,
                "username": target_user.username,
                "pokemon_image": target_user.pokemon_image or "https://via.placeholder.com/50",
                "can_gift": can_gift
            })
            
    return result

@router.get("/requests")
def get_friend_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 查詢別人加我 (accepter是你)，且尚未接受 (is_accepted = False)
    reqs = db.query(Friendship).filter(
        Friendship.accepter_id == current_user.id,
        Friendship.is_accepted == False
    ).all()
    
    result = []
    for r in reqs:
        # 申請人是 requester
        u = db.query(User).filter(User.id == r.requester_id).first()
        if u:
            result.append({
                "request_id": r.id,
                "user_id": u.id,
                "username": u.username,
                "pokemon_image": u.pokemon_image
            })
    return result

@router.post("/add/{target_id}")
def add_friend(target_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if target_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能加自己")
        
    target = db.query(User).filter(User.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="找不到玩家")
        
    # 檢查是否已經有關係 (無論接受與否)
    existing = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.accepter_id == target_id),
            and_(Friendship.requester_id == target_id, Friendship.accepter_id == current_user.id)
        )
    ).first()
    
    if existing:
        if existing.is_accepted:
            return {"message": "已經是好友了"}
        else:
            return {"message": "已經發送過邀請，或對方已邀請你"}
            
    # 建立新邀請
    new_friend = Friendship(
        requester_id=current_user.id,
        accepter_id=target_id,
        is_accepted=False
    )
    db.add(new_friend)
    db.commit()
    
    return {"message": f"已發送好友邀請給 {target.username}"}

@router.post("/accept/{req_id}")
def accept_friend(req_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 確認這個請求是用戶收到的 (accepter_id 必須是自己)
    req = db.query(Friendship).filter(
        Friendship.id == req_id, 
        Friendship.accepter_id == current_user.id,
        Friendship.is_accepted == False
    ).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="找不到邀請或無權限")
        
    req.is_accepted = True
    db.commit()
    
    return {"message": "已接受好友！"}

@router.post("/gift/send/{friend_id}")
def send_gift(friend_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 確認是否為好友
    friend_rel = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.accepter_id == friend_id),
            and_(Friendship.requester_id == friend_id, Friendship.accepter_id == current_user.id)
        ),
        Friendship.is_accepted == True
    ).first()
    
    if not friend_rel:
        raise HTTPException(status_code=400, detail="非好友關係")
        
    target = db.query(User).filter(User.id == friend_id).first()
    if target:
        target.money += 100
        db.commit()
        return {"message": f"已發送 100G 給 {target.username}"}
    
    return {"detail": "發送失敗"}

# 排行榜與簽到保持不變，直接沿用
@router.get("/leaderboard")
def get_leaderboard(type: str = "level", db: Session = Depends(get_db)):
    if type == "money":
        users = db.query(User).order_by(User.money.desc()).limit(10).all()
        return [{"rank": i+1, "username": u.username, "img": u.pokemon_image, "value": f"${u.money}"} for i, u in enumerate(users)]
    elif type == "collection":
        users = db.query(User).all()
        users = sorted(users, key=lambda u: len(u.unlocked_monsters.split(',')) if u.unlocked_monsters else 0, reverse=True)[:10]
        return [{"rank": i+1, "username": u.username, "img": u.pokemon_image, "value": f"{len(u.unlocked_monsters.split(',')) if u.unlocked_monsters else 0}隻"} for i, u in enumerate(users)]
    else: # level
        users = db.query(User).order_by(User.level.desc()).limit(10).all()
        return [{"rank": i+1, "username": u.username, "img": u.pokemon_image, "value": f"Lv.{u.level}"} for i, u in enumerate(users)]
    
@router.get("/daily_checkin")
def daily_checkin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.money += 500
    db.commit()
    return {"message": "簽到成功！獲得 500 Gold"}

@router.get("/admin/init")
def init_admin():
    return {"message": "Admin function not implemented yet"}

@router.post("/chat/send")
def send_chat(content: str = Query(...), current_user: User = Depends(get_current_user)):
    return {"message": "Chat disabled"}

@router.get("/redeem")
def redeem_code(code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if code == "VIP666":
        current_user.money += 10000
        db.commit()
        return {"message": "兌換成功：10000 Gold"}
    return {"detail": "無效的序號"}