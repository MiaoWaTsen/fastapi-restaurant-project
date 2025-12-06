# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError

# --- 1. 資料庫與模型設定 ---
from app.db.session import engine, SessionLocal
from app.models.base import Base 
from app.models import item as item_model
from app.models import user as user_model
from app.core.security import SECRET_KEY, ALGORITHM # 用來解密 Token

# --- 2. 路由與 WebSocket 設定 ---
from app.routers import item
from app.routers import auth
from app.routers import shop
from app.common.websocket import manager

# --- 3. 初始化資料庫 ---
Base.metadata.create_all(bind=engine)

# --- 4. 建立 App ---
app = FastAPI(title="妙蛙宸的怪獸對戰 API")

# --- 5. CORS 設定 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 6. WebSocket 專用通道 (升級版：需驗證身分) ---
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(...) # 從網址參數 ?token=... 取得
):
    # 1. 驗證 Token (這段邏輯跟 auth.py 很像，但 WebSocket 不能用 Depends)
    db = SessionLocal()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            await websocket.close(code=1008)
            return
        
        # 找出是哪位玩家
        user = db.query(user_model.User).filter(user_model.User.username == username).first()
        if user is None:
            await websocket.close(code=1008)
            return
            
        user_id = user.id
        user_name = user.username
        
    except JWTError:
        await websocket.close(code=1008)
        return
    finally:
        db.close()

    # 2. 允許連線 (登記到名冊)
    await manager.connect(user_id, websocket)
    
    # 3. 廣播上線通知
    await manager.broadcast(f"🟢 系統：玩家 [{user_name}] 上線了！")
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # 4. 斷線處理 (從名冊移除)
        manager.disconnect(user_id)
        await manager.broadcast(f"🔴 系統：玩家 [{user_name}] 下線了！")

# --- 7. 掛載路由 ---
app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(shop.router, prefix="/api/v1/shop", tags=["Shop"])

@app.get("/")
def read_root():
    return {"message": "Server is running!", "docs_url": "/docs"}