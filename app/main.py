# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 🔥 1. 關鍵修改：強制引用所有 Model，讓 SQLAlchemy 知道要建表
from app.db.session import engine
from app.models.base import Base
from app.models.user import User
from app.models.friendship import Friendship  # 👈 讓資料庫知道要建這張表
from app.models.mission import UserMission    # 👈 讓資料庫知道要建任務表

# 引入所有路由
from app.routers import auth, shop, social, quest 

# 啟動時自動檢查並建立缺少的表格
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
app.include_router(quest.router, prefix="/api/v1/quests", tags=["quests"]) # 🔥 2. 補上這行解決 404

@app.get("/")
def read_root():
    return {"message": "Pokemon Battle Royale API is running!"}