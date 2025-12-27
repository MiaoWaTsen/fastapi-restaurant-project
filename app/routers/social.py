# app/routers/social.py

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import json
import uuid  # 🔥 新增這個，為了生成卡比獸的 UID
from datetime import datetime

from app.db.session import get_db
from app.common.deps import get_current_user
from app.common.websocket import manager
from app.models.user import User
from app.models.friendship import Friendship

router = APIRouter()

# ===========================
# 聊天室 & 系統廣播
# ===========================
@router.post("/chat/send")
async def send_chat(content: str = Query(...), current_user: User = Depends(get_current_user)):
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
        all_users = query.all()
        data = []
        for u in all_users:
            count = len(u.unlocked_monsters.split(',')) if u.unlocked_monsters else 0
            data.append({"username": u.username, "img": u.pokemon_image, "value": count})
        data.sort(key=lambda x: x["value"], reverse=True)
        return [{"rank": i+1, **d} for i, d in enumerate(data[:10])]
    else: 
        query = query.order_by(User.level.desc(), User.exp.desc())
        
    users = query.limit(10).all()
    return [{"rank": i+1, "username": u.username, "img": u.pokemon_image, "value": getattr(u, type if type != 'collection' else 'level')} for i, u in enumerate(users)]

# ===========================
# 好友系統
# ===========================

@router.get("/list")
def get_friend_list(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    friends_relations = db.query(Friendship).filter(
        or_(Friendship.requester_id == current_user.id, Friendship.accepter_id == current_user.id),
        Friendship.is_accepted == True
    ).all()
    
    friends_data = []
    for rel in friends_relations:
        friend_user = rel.accepter if rel.requester_id == current_user.id else rel.requester
        friends_data.append({
            "id": friend_user.id,
            "username": friend_user.username,
            "pokemon_image": friend_user.pokemon_image,
            "is_online": False,
            "can_gift": True
        })
    return friends_data

@router.get("/requests")
def get_friend_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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

@router.post("/add/{target_id}")
async def send_friend_request(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if target_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能加自己好友")
    target = db.query(User).filter(User.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="找不到該玩家")

    existing = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.accepter_id == target_id),
            and_(Friendship.requester_id == target_id, Friendship.accepter_id == current_user.id)
        )
    ).first()
    
    if existing:
        if existing.is_accepted: return {"message": "你們已經是好友了"}
        return {"message": "已經發送過申請，或對方已邀請你"}

    new_request = Friendship(requester_id=current_user.id, accepter_id=target_id, is_accepted=False)
    db.add(new_request)
    db.commit()
    return {"message": f"已向 {target.username} 發送好友邀請"}

@router.post("/accept/{request_id}")
def accept_friend_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    request = db.query(Friendship).filter(Friendship.id == request_id, Friendship.accepter_id == current_user.id).first()
    if not request: raise HTTPException(status_code=404, detail="找不到邀請")
    request.is_accepted = True
    db.commit()
    return {"message": f"已接受 {request.requester.username} 的好友邀請"}

@router.post("/remove/{target_id}")
def remove_friend(target_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
    target = db.query(User).filter(User.id == target_id).first()
    if target:
        target.money += 100
        db.commit()
        return {"message": f"已送給 {target.username} 100G"}
    raise HTTPException(status_code=404, detail="用戶不存在")

# ===========================
# 🔥 兌換碼系統 (含一次性檢查) 🔥
# ===========================
@router.post("/redeem")
def redeem_code(code: str = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. 讀取背包與已使用紀錄
    try:
        inv = json.loads(current_user.inventory) if current_user.inventory else {}
    except:
        inv = {}
        
    # 初始化已使用清單
    if "redeemed_codes" not in inv:
        inv["redeemed_codes"] = []
    
    # 2. 檢查是否用過
    if code in inv["redeemed_codes"]:
        return {"detail": "此序號您已經使用過了！"}

    msg = ""
    success = False

    # 3. 判斷序號獎勵
    if code == "compensation_gold":
        current_user.money += 30000
        msg = "補償領取：💰 30,000 G"
        success = True
        
    elif code == "compensation_candy":
        inv["candy"] = inv.get("candy", 0) + 30
        msg = "補償領取：🍬 神奇糖果 x30"
        success = True
        
    elif code == "compensation_goldencandy":
        inv["golden_candy"] = inv.get("golden_candy", 0) + 5
        msg = "補償領取：✨ 黃金糖果 x5"
        success = True
        
    # 支援您的拼音 "conmoenstion" 以防萬一，同時支援正確拼法
    elif code == "compensation_snorlax" or code == "conmoenstion_snorlax":
        # 生成 IV 80 的卡比獸
        new_mon = {
            "uid": str(uuid.uuid4()),
            "name": "卡比獸",
            "iv": 80,
            "lv": 1,
            "exp": 0
        }
        try:
            box = json.loads(current_user.pokemon_storage) if current_user.pokemon_storage else []
        except:
            box = []
            
        box.append(new_mon)
        current_user.pokemon_storage = json.dumps(box)
        
        # 解鎖圖鑑
        unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
        if "卡比獸" not in unlocked:
            unlocked.append("卡比獸")
            current_user.unlocked_monsters = ",".join(unlocked)
            
        msg = "補償領取：💤 卡比獸 (IV 80) 已放入盒子！"
        success = True

    # 舊有的測試碼
    elif code == "MWT2025":
        current_user.money += 5000
        msg = "兌換成功！獲得 5000 G"
        success = True
    elif code == "LOVEPOKEMON":
        inv["candy"] = inv.get("candy", 0) + 5
        msg = "兌換成功！獲得 5 顆神奇糖果"
        success = True

    # 4. 結算
    if success:
        inv["redeemed_codes"].append(code) # 記錄已使用
        current_user.inventory = json.dumps(inv)
        db.commit()
        return {"message": msg}
    else:
        return {"detail": "無效的序號"}