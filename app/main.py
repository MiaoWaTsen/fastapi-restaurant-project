# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- 1. 資料庫設定 ---
from app.db.session import engine
# 匯入共用的 Base
from app.models.base import Base 

# ⚠️ 關鍵：必須匯入所有的 Model，SQLAlchemy 才會知道要建立哪些資料表
from app.models import item as item_model
from app.models import user as user_model

# --- 2. 路由設定 ---
from app.routers import item  # 怪獸系統
from app.routers import auth  # 會員系統

# --- 3. 初始化資料庫 ---
# 啟動時自動建立 tables (monsters 和 users)
Base.metadata.create_all(bind=engine)

# --- 4. 建立 App ---
app = FastAPI(title="妙蛙宸的怪獸對戰 API")

# --- 5. CORS 設定 (通行證) ---
# 這一塊就是解決 "blocked" 錯誤的關鍵！
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允許所有來源 (包含 file://, localhost, vercel)
    allow_credentials=True,
    allow_methods=["*"], # 允許所有動作 (GET, POST, PUT, DELETE)
    allow_headers=["*"], # 允許所有標頭
)

# --- 6. 掛載路由 (Routers) ---
app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

# --- 7. 首頁測試 ---
@app.get("/")
def read_root():
    return {"message": "Server is running!", "docs_url": "/docs"}