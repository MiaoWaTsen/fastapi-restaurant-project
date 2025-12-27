# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 資料庫與模型
from app.db.session import engine
from app.models.base import Base
from app.models.user import User
from app.models.friendship import Friendship  # ✅ 保留這個，因為好友系統需要建表
# ❌ 移除 app.models.mission，因為目前的任務是用 JSON 存的，不需要這行

# 引入所有路由
from app.routers import auth, shop, social, quest 

# 啟動時自動檢查並建立缺少的表格 (例如 friendships)
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(shop.router, prefix="/api/v1/shop", tags=["shop"])
app.include_router(social.router, prefix="/api/v1/social", tags=["social"])
app.include_router(quest.router, prefix="/api/v1/quests", tags=["quests"])

@app.get("/")
def read_root():
    return {"message": "Pokemon Battle Royale API is running!"}