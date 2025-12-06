# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- 1. 資料庫與模型設定 ---
from app.db.session import engine
# 這裡要匯入共用的 Base，而不是各自檔案裡的 Base
from app.models.base import Base 

# ⚠️ 關鍵步驟：必須匯入所有的 Model 檔案
# 這樣 SQLAlchemy 在執行 create_all 時，才知道要建立 'monsters' 和 'users' 這兩張表
from app.models import item as item_model
from app.models import user as user_model

# --- 2. 路由設定 ---
from app.routers import item  # 怪獸相關
from app.routers import auth  # 登入註冊相關 (新增的)

# --- 3. 初始化資料庫 ---
# 這行指令會去檢查資料庫，如果沒有 tables 就會自動建立
# (因為我們新增了 users 表，這步很重要)
Base.metadata.create_all(bind=engine)

# --- 4. 應用程式實例 ---
app = FastAPI(title="妙蛙宸的怪獸對戰 API")

# --- 5. CORS 設定 (允許前端連線) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允許所有網域連線 (包含 Vercel 和 Localhost)
    allow_credentials=True,
    allow_methods=["*"], # 允許所有方法 (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],
)

# --- 6. 掛載路由 ---
# 怪獸系統 (原本的)
app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])

# 會員系統 (新增的)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

# --- 7. 首頁測試 ---
@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Monster Battle RPG API!",
        "docs": "/docs"
    }