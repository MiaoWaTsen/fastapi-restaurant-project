# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine
from app.db.base_class import Base
# 確保引入所有 Router 與 Model 以便觸發建表
from app.routers import auth, shop, social, quest
from app.models import user

# 🔥 核心邏輯：自動建立所有定義的新表格 (包含 users_v11)
# 因為我們已經改了 table name，SQLAlchemy 會自動幫我們建新表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pokemon RPG API")

# 設定 CORS (允許前端連線)
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
    return {"message": "Welcome to Pokemon RPG API - V11 Stable"}