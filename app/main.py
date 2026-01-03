# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine
from app.db.base_class import Base
from app.routers import auth, shop, social, quest
from app.models import user # 確保 User 模型被載入以觸發建表

# 建立所有定義在 Base 中的表格 (包含 users_v11)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pokemon RPG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(shop.router, prefix="/api/v1/shop", tags=["shop"])
app.include_router(social.router, prefix="/api/v1/social", tags=["social"])
app.include_router(quest.router, prefix="/api/v1/quests", tags=["quests"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Pokemon RPG API - V11 Reset"}