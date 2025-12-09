# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError

from app.db.session import engine, SessionLocal
from app.models.base import Base 
from app.models import item as item_model
from app.models import user as user_model
from app.core.security import SECRET_KEY, ALGORITHM

from app.routers import item, auth, shop, quest # 🔥 匯入 quest
from app.common.websocket import manager

Base.metadata.create_all(bind=engine)

app = FastAPI(title="寶可夢大亂鬥 API")

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

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])
app.include_router(shop.router, prefix="/api/v1/shop", tags=["Shop"])
app.include_router(quest.router, prefix="/api/v1/quests", tags=["Quest"]) # 🔥 掛載 quest

@app.get("/")
def read_root():
    return {"message": "Server is running!"}