# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError
import os
import logging
import sys

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="寶可夢大亂鬥 API")

# 1. CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 資料庫連線初始化
db_status = "Not Connected"
try:
    from app.db.session import engine, SessionLocal
    from app.models.base import Base
    from app.models import item as item_model
    from app.models import user as user_model
    from app.core.security import SECRET_KEY, ALGORITHM
    from app.routers import item, auth, shop, quest
    # 🔥 確保這個檔案存在且正確 🔥
    from app.common.websocket import manager

    logger.info("正在連線資料庫...")
    Base.metadata.create_all(bind=engine)
    logger.info("資料庫連線成功！")
    db_status = "Connected"
    
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])
    app.include_router(shop.router, prefix="/api/v1/shop", tags=["Shop"])
    app.include_router(quest.router, prefix="/api/v1/quests", tags=["Quest"])

except Exception as e:
    logger.error(f"❌ 啟動失敗: {str(e)}")
    db_status = f"Error: {str(e)}"

# 3. 頁面與健康檢查
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

# 🔥 4. WebSocket 強化版 (含錯誤處理) 🔥
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()
    
    # 如果資料庫沒連上，直接斷開
    if db_status != "Connected":
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    user_id = None
    user_name = "Unknown"
    
    try:
        # 驗證 Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user = db.query(user_model.User).filter(user_model.User.username == username).first()
        if not user:
            logger.warning("WebSocket: User not found")
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

    # 連線管理
    await manager.connect(user_id, websocket)
    logger.info(f"WebSocket Connected: {user_name} ({user_id})")
    
    try:
        while True:
            # 保持連線，接收訊息 (目前只做 ping pong 或忽略)
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket Disconnected: {user_name}")
        manager.disconnect(user_id)
    except Exception as e:
        # 🔥 捕捉其他未知錯誤，防止 Crash 🔥
        logger.error(f"WebSocket Runtime Error: {e}")
        manager.disconnect(user_id)