from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import json
from datetime import datetime

from app.db.session import get_db
from app.common.deps import get_current_user
from app.common.websocket import manager
from app.models.user import User
from app.models.friendship import Friendship # 🔥 引用新模型

router = APIRouter()

# ===========================
# 聊天室 & 系統廣播
# ===========================
@router.post("/chat/send")
async def send_chat(content: str = Query(...), current_user: User = Depends(get_current_user)):
    # 1. 全服聊天室訊息被吃掉修復：確保格式正確且有廣播
    msg = f"CHAT|[{current_user.username}]: {content}"
    await manager.broadcast(msg)
    return {"message": "sent"}

@router.post("/log/frontend")
async def log_frontend_error(payload: dict):
    print(f"🚨 前端錯誤: {payload}")
    return {"status": "logged"}

@router.get("/leaderboard")
def get_leaderboard(type: str = "level", db: Session = Depends(get_db)):
    query = db.query(User)
    if type == "money":
        query = query.order_by(User.money.desc())
    elif type == "collection":
        # 簡易排序，實際建議用 SQL count
        all_users = query.all()
        data = []
        for u in all_users:
            count = len(u.unlocked_monsters.split(',')) if u.unlocked_monsters else 0
            data.append({"username": u.username, "img": u.pokemon_image, "value": count})
        data.sort(key=lambda x: x["value"], reverse=True)
        return [{"rank": i+1, **d} for i, d in enumerate(data[:10])]
    else: # level
        query = query.order_by(User.level.desc(), User.exp.desc())
        
    users = query.limit(10).all()
    return [{"rank": i+1, "username": u.username, "img": u.pokemon_image, "value": getattr(u, type if type != 'collection' else 'level')} for i, u in enumerate(users)]

# ===========================
# 好友系統 (改為邀請制)
# ===========================

# 取得我的好友列表 (已同意)
@router.get("/list")
def get_friend_list(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 搜尋所有我是邀請者或接收者，且 is_accepted=True 的紀錄
    friends_relations = db.query(Friendship).filter(
        or_(Friendship.requester_id == current_user.id, Friendship.accepter_id == current_user.id),
        Friendship.is_accepted == True
    ).all()
    
    friends_data = []
    for rel in friends_relations:
        # 判斷對方是誰
        friend_user = rel.accepter if rel.requester_id == current_user.id else rel.requester
        friends_data.append({
            "id": friend_user.id,
            "username": friend_user.username,
            "pokemon_image": friend_user.pokemon_image, # 🔥 3. 顯示好友頭像
            "is_online": False, # 暫時未實作線上狀態偵測
            "can_gift": True
        })
    return friends_data

# 取得待確認的好友邀請
@router.get("/requests")
def get_friend_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 查詢「接收者是我」且「未同意」的紀錄
    requests = db.query(Friendship).filter(
        Friendship.accepter_id == current_user.id,
        Friendship.is_accepted == False
    ).all()
    
    return [{
        "request_id": r.id,
        "requester_id": r.requester.id,
        "username": r.requester.username,
        "pokemon_image": r.requester.pokemon_image
    } for r in requests]

# 發送好友邀請
@router.post("/add/{target_id}")
async def send_friend_request(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if target_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能加自己好友")
        
    target = db.query(User).filter(User.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="找不到該玩家")

    # 檢查是否已經有關係 (無論是申請中還是已好友)
    existing = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.accepter_id == target_id),
            and_(Friendship.requester_id == target_id, Friendship.accepter_id == current_user.id)
        )
    ).first()
    
    if existing:
        if existing.is_accepted:
            return {"message": "你們已經是好友了"}
        return {"message": "已經發送過申請，或對方已邀請你"}

    # 🔥 4. 建立申請紀錄
    new_request = Friendship(requester_id=current_user.id, accepter_id=target_id, is_accepted=False)
    db.add(new_request)
    db.commit()
    
    # 嘗試通知對方 (如果在線)
    # await manager.send_personal_message(f"EVENT:FRIEND_REQ|{current_user.username}", target_id)
    
    return {"message": f"已向 {target.username} 發送好友邀請"}

# 同意好友邀請
@router.post("/accept/{request_id}")
def accept_friend_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    request = db.query(Friendship).filter(
        Friendship.id == request_id,
        Friendship.accepter_id == current_user.id # 確保是審核自己的邀請
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="找不到邀請")
        
    request.is_accepted = True
    db.commit()
    return {"message": f"已接受 {request.requester.username} 的好友邀請"}

# 拒絕/刪除好友
@router.post("/remove/{target_id}")
def remove_friend(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 找出兩人的關係
    relation = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.accepter_id == target_id),
            and_(Friendship.requester_id == target_id, Friendship.accepter_id == current_user.id)
        )
    ).first()
    
    if relation:
        db.delete(relation)
        db.commit()
        return {"message": "已刪除/拒絕"}
    raise HTTPException(status_code=404, detail="關係不存在")

@router.post("/gift/send/{target_id}")
def send_gift(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 簡單實作：送對方 100 G，自己不扣
    target = db.query(User).filter(User.id == target_id).first()
    if target:
        target.money += 100
        db.commit()
        return {"message": f"已送給 {target.username} 100G"}
    raise HTTPException(status_code=404, detail="用戶不存在")

# 兌換碼 (邏輯不變)
@router.post("/redeem")
def redeem_code(code: str = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if code == "MWT2025":
        current_user.money += 5000
        db.commit()
        return {"message": "兌換成功！獲得 5000 G"}
    elif code == "LOVEPOKEMON":
        inv = json.loads(current_user.inventory)
        inv["candy"] = inv.get("candy", 0) + 5
        current_user.inventory = json.dumps(inv)
        db.commit()
        return {"message": "兌換成功！獲得 5 顆神奇糖果"}
    return {"detail": "無效的序號"}