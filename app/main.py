# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine
from app.db.base_class import Base
from app.routers import auth, shop, quest

# 自動建立表格 (包含 users_v11)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pokemon RPG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 路由掛載策略 🔥
# 1. 認證路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# 2. 商店/戰鬥/社交路由 (全部由 shop.py 處理)
# 前端有時候呼叫 /shop/... 有時候呼叫 /social/...，這裡直接雙重掛載避免 404
app.include_router(shop.router, prefix="/api/v1/shop", tags=["shop"])
app.include_router(shop.router, prefix="/api/v1/social", tags=["social"])

# 3. 任務路由
app.include_router(quest.router, prefix="/api/v1/quests", tags=["quests"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Pokemon RPG API - V2.11.24 Stable"}