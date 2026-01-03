# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.db.session import engine
from app.db.base_class import Base
from app.routers import auth, shop, social, quest

# 1. 建立資料庫表格 (僅限新表)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pokemon RPG API")

# 2. 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 🔥 資料庫自動修補腳本 (Auto-Migration) 🔥
# 這段程式碼會在伺服器啟動時執行，自動補上缺少的欄位！
@app.on_event("startup")
def fix_database_schema():
    print("正在檢查並修復資料庫結構...")
    with engine.connect() as conn:
        # 強制開啟自動提交模式
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        
        # 定義所有可能缺少的欄位及其預設值
        columns_to_add = [
            ("level", "INTEGER DEFAULT 1"),
            ("exp", "INTEGER DEFAULT 0"),
            ("money", "INTEGER DEFAULT 1000"),
            ("pet_level", "INTEGER DEFAULT 1"),
            ("pet_exp", "INTEGER DEFAULT 0"),
            ("hp", "INTEGER DEFAULT 100"),
            ("max_hp", "INTEGER DEFAULT 100"),
            ("attack", "INTEGER DEFAULT 10"),
            ("pokemon_name", "VARCHAR DEFAULT '皮卡丘'"),
            ("pokemon_image", "VARCHAR DEFAULT 'https://img.pokemondb.net/artwork/large/pikachu.jpg'"),
            ("active_pokemon_uid", "VARCHAR"),
            ("pokemon_storage", "VARCHAR DEFAULT '[]'"),
            ("inventory", "VARCHAR DEFAULT '{}'"),
            ("unlocked_monsters", "VARCHAR DEFAULT ''"),
            ("quests", "VARCHAR DEFAULT '[]'"),
            # 如果您還想要 last_checkin_date，也可以加回去，但我們現在用 inventory 存了
        ]

        for col_name, col_type in columns_to_add:
            try:
                # 嘗試新增欄位，如果已存在會報錯，我們就忽略錯誤
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                print(f"✅ 檢查/修復欄位: {col_name}")
            except Exception as e:
                print(f"⚠️ 欄位 {col_name} 檢查跳過或失敗: {e}")
                
    print("資料庫結構修復完成！")

# 4. 註冊路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(shop.router, prefix="/api/v1/shop", tags=["shop"])
app.include_router(social.router, prefix="/api/v1/social", tags=["social"]) # V2.11.16: 確保 social 被註冊
app.include_router(quest.router, prefix="/api/v1/quests", tags=["quests"]) # V2.11.16: 確保 quest 被註冊

@app.get("/")
def read_root():
    return {"message": "Welcome to Pokemon RPG API V2.11.16"}