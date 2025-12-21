# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from jose import jwt
import os
import logging
import sys

# 設定日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

app = FastAPI(title="寶可夢大亂鬥 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_status = "Not Connected"
try:
    from app.db.session import engine, SessionLocal
    from app.models.base import Base
    from app.models import item as item_model
    from app.models import user as user_model
    # 🔥 1. 引入新 Model，這樣 create_all 才會建立表格 🔥
    from app.models import friend as friend_model 
    
    from app.core.security import SECRET_KEY, ALGORITHM
    from app.routers import item, auth, shop, quest
    # 🔥 2. 引入新 Router 🔥
    from app.routers import social
    
    from app.common.websocket import manager

    logger.info("正在連線資料庫...")
    # 這行會自動檢查：如果 users 表存在就不動，發現 friends 表不存在就會建立
    Base.metadata.create_all(bind=engine)
    logger.info("資料庫連線成功！")
    db_status = "Connected"
    
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])
    app.include_router(shop.router, prefix="/api/v1/shop", tags=["Shop"])
    app.include_router(quest.router, prefix="/api/v1/quests", tags=["Quest"])
    # 🔥 3. 掛載新 Router 🔥
    app.include_router(social.router, prefix="/api/v1/social", tags=["Social"])

except Exception as e:
    logger.error(f"❌ 啟動失敗: {str(e)}")
    db_status = f"Error: {str(e)}"

@app.get("/health")
def health_check():
    return {"status": "ok", "db": db_status}

@app.get("/", response_class=HTMLResponse)
def read_root():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return f"<h1>Server Running. DB: {db_status}</h1>"

@app.get("/login.html", response_class=HTMLResponse)
def read_login():
    if os.path.exists("login.html"):
        with open("login.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Login page not found</h1>"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()
    if db_status != "Connected":
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    user_id = None
    user_name = "Unknown"
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user = db.query(user_model.User).filter(user_model.User.username == username).first()
        if not user:
            await websocket.close(code=1008)
            return
        user_id = user.id
        user_name = user.username
    except Exception as e:
        logger.error(f"WebSocket Auth Error: {e}")
        await websocket.close(code=1008)
        return
    finally:
        db.close()

    await manager.connect(user_id, websocket)
    logger.info(f"WebSocket Connected: {user_name} ({user_id})")
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket Disconnected: {user_name}")
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket Runtime Error: {e}")
        manager.disconnect(user_id)