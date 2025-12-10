# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
# 🔥 新增：HTMLResponse 用來回傳網頁 🔥
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError
import os

from app.db.session import engine, SessionLocal
from app.models.base import Base 
# 確保模型被載入
from app.models import item as item_model
from app.models import user as user_model
from app.core.security import SECRET_KEY, ALGORITHM

# 引入路由
from app.routers import item, auth, shop, quest
from app.common.websocket import manager

# 建立資料庫表格
Base.metadata.create_all(bind=engine)

app = FastAPI(title="寶可夢大亂鬥 API")

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
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
    except JWTError:
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

# 🔥 修改這裡：讀取並回傳 index.html 🔥
@app.get("/", response_class=HTMLResponse)
def read_root():
    # 嘗試讀取根目錄下的 index.html
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>錯誤：找不到 index.html</h1><p>請確認 index.html 檔案位於專案根目錄。</p>"