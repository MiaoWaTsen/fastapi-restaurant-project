# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # 1. 新增：匯入 CORS 套件
from app.routers import item
from app.db.session import engine
from app.models import item as item_model

item_model.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- 2. 新增：設定通行證 (CORS) ---
# 這段設定允許「任何來源 (*」連線到你的 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允許所有網域 (正式上線時通常會限制，但練習時全開沒關係)
    allow_credentials=True,
    allow_methods=["*"], # 允許所有方法 (GET, POST, PUT, DELETE...)
    allow_headers=["*"], # 允許所有標頭
)
# -------------------------------

app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])

@app.get("/")
def read_root():
    return {"Hello": "World"}