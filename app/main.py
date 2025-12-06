# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# --- 1. 資料庫與模型設定 ---
from app.db.session import engine
# 匯入共用的 Base
from app.models.base import Base 

# ⚠️ 關鍵：必須匯入所有的 Model，SQLAlchemy 才會知道要建立哪些資料表
from app.models import item as item_model
from app.models import user as user_model

# --- 2. 路由與 WebSocket 設定 ---
from app.routers import item  # 怪獸系統
from app.routers import auth  # 會員系統
from app.common.websocket import manager # 匯入我們剛剛寫的廣播站長

from app.routers import shop

# --- 3. 初始化資料庫 ---
# 啟動時自動建立 tables (monsters 和 users)
Base.metadata.create_all(bind=engine)

# --- 4. 建立 App ---
app = FastAPI(title="妙蛙宸的怪獸對戰 API")

# --- 5. CORS 設定 (通行證) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允許所有來源 (包含 file://, localhost, vercel)
    allow_credentials=True,
    allow_methods=["*"], # 允許所有動作 (GET, POST, PUT, DELETE)
    allow_headers=["*"], # 允許所有標頭
)

# --- 6. WebSocket 專用通道 (新增功能) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 保持連線，持續監聽（雖然目前我們只發不收，但必須維持迴圈）
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- 7. 掛載路由 (Routers) ---
app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(shop.router, prefix="/api/v1/shop", tags=["Shop"])
# --- 8. 首頁測試 ---
@app.get("/")
def read_root():
    return {"message": "Server is running!", "docs_url": "/docs"}