# app/routers/social.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import json
from datetime import datetime

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.models.friend import Friend # 請確認您有這個 Model，如果沒有請看下面備註

router = APIRouter()

# ---------------------------------------------------------
# 如果您沒有 app/models/friend.py，請確保資料庫有 friend 表
# 這裡假設 Friend 模型有: id, user_id, friend_id, status
# ---------------------------------------------------------

@router.get("/list")
def get_friend_list(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 查詢所有 status = 'ACCEPTED' 的紀錄
    # 邏輯：我是發起人 (user_id=me) 或者 我是接收人 (friend_id=me)
    friends_rel = db.query(Friend).filter(
        or_(Friend.user_id == current_user.id, Friend.friend_id == current_user.id),
        Friend.status == 'ACCEPTED'
    ).all()
    
    result = []
    for rel in friends_rel:
        # 判斷誰是對方
        target_id = rel.friend_id if rel.user_id == current_user.id else rel.user_id
        target_user = db.query(User).filter(User.id == target_id).first()
        
        if target_user:
            # 判斷是否能送禮 (這裡簡單模擬，實際上可能要檢查上次送禮時間)
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
    # 查詢別人加我，且狀態是 PENDING 的
    reqs = db.query(Friend).filter(
        Friend.friend_id == current_user.id,
        Friend.status == 'PENDING'
    ).all()
    
    result = []
    for r in reqs:
        u = db.query(User).filter(User.id == r.user_id).first()
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
        
    # 檢查是否已經有關係
    existing = db.query(Friend).filter(
        or_(
            and_(Friend.user_id == current_user.id, Friend.friend_id == target_id),
            and_(Friend.user_id == target_id, Friend.friend_id == current_user.id)
        )
    ).first()
    
    if existing:
        if existing.status == 'ACCEPTED':
            return {"message": "已經是好友了"}
        if existing.status == 'PENDING':
            return {"message": "已經發送過邀請，或對方已邀請你"}
            
    # 建立新邀請
    new_friend = Friend(
        user_id=current_user.id,
        friend_id=target_id,
        status='PENDING',
        created_at=datetime.utcnow()
    )
    db.add(new_friend)
    db.commit()
    
    return {"message": f"已發送好友邀請給 {target.username}"}

@router.post("/accept/{req_id}")
def accept_friend(req_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 確認這個請求是用戶收到的
    req = db.query(Friend).filter(
        Friend.id == req_id, 
        Friend.friend_id == current_user.id,
        Friend.status == 'PENDING'
    ).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="找不到邀請或無權限")
        
    req.status = 'ACCEPTED'
    db.commit()
    
    return {"message": "已接受好友！"}

@router.post("/gift/send/{friend_id}")
def send_gift(friend_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 這裡實作送禮邏輯
    # 簡單版：給對方 100G
    friend_rel = db.query(Friend).filter(
        or_(
            and_(Friend.user_id == current_user.id, Friend.friend_id == friend_id),
            and_(Friend.user_id == friend_id, Friend.friend_id == current_user.id)
        ),
        Friend.status == 'ACCEPTED'
    ).first()
    
    if not friend_rel:
        raise HTTPException(status_code=400, detail="非好友關係")
        
    target = db.query(User).filter(User.id == friend_id).first()
    if target:
        target.money += 100
        db.commit()
        return {"message": f"已發送 100G 給 {target.username}"}
    
    return {"detail": "發送失敗"}

# 排行榜 (因為 index.html 會呼叫 social/leaderboard)
@router.get("/leaderboard")
def get_leaderboard(type: str = "level", db: Session = Depends(get_db)):
    if type == "money":
        users = db.query(User).order_by(User.money.desc()).limit(10).all()
        return [{"rank": i+1, "username": u.username, "img": u.pokemon_image, "value": f"${u.money}"} for i, u in enumerate(users)]
    elif type == "collection":
        # 簡單模擬，實際應計算 unlocked_monsters 長度
        users = db.query(User).all()
        # 排序邏輯略，回傳等級排行代替
        users = sorted(users, key=lambda u: len(u.unlocked_monsters.split(',')) if u.unlocked_monsters else 0, reverse=True)[:10]
        return [{"rank": i+1, "username": u.username, "img": u.pokemon_image, "value": f"{len(u.unlocked_monsters.split(',')) if u.unlocked_monsters else 0}隻"} for i, u in enumerate(users)]
    else: # level
        users = db.query(User).order_by(User.level.desc()).limit(10).all()
        return [{"rank": i+1, "username": u.username, "img": u.pokemon_image, "value": f"Lv.{u.level}"} for i, u in enumerate(users)]
    
@router.get("/daily_checkin")
def daily_checkin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 簡單簽到：送 500G
    current_user.money += 500
    db.commit()
    return {"message": "簽到成功！獲得 500 Gold"}

# 管理員初始化
@router.get("/admin/init")
def init_admin():
    return {"message": "Admin function not implemented yet"}

# 聊天發送 (雖然前端移除了，但保留接口防報錯)
@router.post("/chat/send")
def send_chat(content: str = Query(...), current_user: User = Depends(get_current_user)):
    return {"message": "Chat disabled"}

# 兌換碼
@router.get("/redeem")
def redeem_code(code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if code == "VIP666":
        current_user.money += 10000
        db.commit()
        return {"message": "兌換成功：10000 Gold"}
    return {"detail": "無效的序號"}