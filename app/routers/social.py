# app/routers/social.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List

from app.db.session import get_db
from app.models.user import User
from app.models.friend import Friend
from app.common.deps import get_current_user

router = APIRouter()

@router.get("/list")
def get_friends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 找出所有 "我加別人" 或 "別人加我" 且狀態是 ACCEPTED 的紀錄
    friends_rel = db.query(Friend).filter(
        or_(Friend.user_id == current_user.id, Friend.friend_id == current_user.id),
        Friend.status == "ACCEPTED"
    ).all()
    
    friend_ids = []
    for f in friends_rel:
        if f.user_id == current_user.id: friend_ids.append(f.friend_id)
        else: friend_ids.append(f.user_id)
        
    if not friend_ids: return []
    
    # 撈出這些好友的詳細資料
    friends = db.query(User).filter(User.id.in_(friend_ids)).all()
    return [
        {"id": u.id, "username": u.username, "level": u.level, "pet": u.pokemon_name, "img": u.pokemon_image}
        for u in friends
    ]

@router.get("/requests")
def get_friend_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 找出 "別人加我" 且狀態是 PENDING 的
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
    
    # 檢查是否已經是好友或申請過
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