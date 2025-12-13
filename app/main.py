# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from jose import jwt, JWTError
import os
import logging
import sys

# 設定日誌格式，確保能輸出到 Zeabur 控制台
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="寶可夢大亂鬥 API")

# 1. CORS 設定 (允許所有)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 嘗試引入資料庫 (使用 try-catch 包裹防止閃退)
db_status = "Not Connected"
try:
    from app.db.session import engine, SessionLocal
    from app.models.base import Base
    # 嘗試載入 Model
    from app.models import item as item_model
    from app.models import user as user_model
    from app.core.security import SECRET_KEY, ALGORITHM
    from app.routers import item, auth, shop, quest
    from app.common.websocket import manager

    # 嘗試建立表格
    logger.info("正在連線資料庫...")
    Base.metadata.create_all(bind=engine)
    logger.info("資料庫連線成功！")
    db_status = "Connected"
    
    # 掛載路由
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])
    app.include_router(shop.router, prefix="/api/v1/shop", tags=["Shop"])
    app.include_router(quest.router, prefix="/api/v1/quests", tags=["Quest"])

except Exception as e:
    logger.error(f"❌ 嚴重錯誤：啟動失敗 - {str(e)}")
    db_status = f"Error: {str(e)}"
    # 這裡不拋出錯誤，讓伺服器繼續運行，這樣你才能看到 health check 的錯誤訊息

# 3. 健康檢查 API (救命用)
@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "server": "running", 
        "database": db_status
    }

@app.get("/", response_class=HTMLResponse)
def read_root():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return f"<h1>Server Running. DB Status: {db_status}</h1>"

@app.get("/login.html", response_class=HTMLResponse)
def read_login():
    if os.path.exists("login.html"):
        with open("login.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Login page not found</h1>"

# WebSocket 路由 (如果 DB 失敗，這裡會報錯但不會讓伺服器死掉)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()
    if db_status != "Connected":
        await websocket.close(code=1008, reason="Database Error")
        return

    db = SessionLocal()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user = db.query(user_model.User).filter(user_model.User.username == username).first()
        if not user:
            await websocket.close(code=1008)
            return
        user_id = user.id
    except Exception as e:
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