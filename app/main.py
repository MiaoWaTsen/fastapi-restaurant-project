# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError
import os
import logging # 🔥 新增 logging

from app.db.session import engine, SessionLocal
from app.models.base import Base 
# 確保載入所有 Model
from app.models import item as item_model
from app.models import user as user_model
from app.core.security import SECRET_KEY, ALGORITHM

from app.routers import item, auth, shop, quest
from app.common.websocket import manager

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="寶可夢大亂鬥 API")

# 🔥 1. CORS 設定最優先執行 🔥
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允許所有來源 (除錯用)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 2. 資料庫連線防呆 (關鍵修改) 🔥
try:
    logger.info("正在嘗試建立資料庫表格...")
    Base.metadata.create_all(bind=engine)
    logger.info("資料庫表格建立成功！")
except Exception as e:
    # 就算資料庫連線失敗，也只印出錯誤，不要讓程式崩潰
    logger.error(f"⚠️ 資料庫連線失敗，請檢查環境變數: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # WebSocket 連線邏輯 (保持不變)
    await websocket.accept() # 先接受連線，再驗證
    
    db = SessionLocal()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            await websocket.close(code=1008)
            return
        
        user = db.query(user_model.User).filter(user_model.User.username == username).first()
        if not user:
            await websocket.close(code=1008)
            return
            
        user_id = user.id
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        await websocket.close(code=1008)
        return
    finally:
        db.close()

    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# 掛載路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])
app.include_router(shop.router, prefix="/api/v1/shop", tags=["Shop"])
app.include_router(quest.router, prefix="/api/v1/quests", tags=["Quest"])

# 根目錄檢查
@app.get("/", response_class=HTMLResponse)
def read_root():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Server is Running! (index.html not found)</h1>"

@app.get("/login.html", response_class=HTMLResponse)
def read_login():
    if os.path.exists("login.html"):
        with open("login.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Login page not found</h1>"

# 🔥 新增健康檢查 API 🔥
@app.get("/health")
def health_check():
    return {"status": "ok", "db": "unknown (check logs)"}