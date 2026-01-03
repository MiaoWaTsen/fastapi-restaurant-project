# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine
from app.db.base_class import Base
from app.routers import auth, shop, quest

# 自動建立表格 (包含 users_v11, gyms, friendships)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pokemon RPG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由掛載
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(shop.router, prefix="/api/v1/shop", tags=["shop"])
app.include_router(shop.router, prefix="/api/v1/social", tags=["social"])
app.include_router(quest.router, prefix="/api/v1/quests", tags=["quests"])

# 🔥 V2.12.3: 啟動時初始化道館
@app.on_event("startup")
def on_startup():
    shop.init_gyms()

@app.get("/")
def read_root():
    return {"message": "Welcome to Pokemon RPG API - V12 Stable"}