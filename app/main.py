# app/main.py

from fastapi import FastAPI
from app.routers import item
from app.db.session import engine # <-- 1. 匯入「連線通道」
from app.models import item as item_model # <-- 2. 匯入你的「item 食譜」

# --- 關鍵指令 ---
# 告訴 SQLAlchemy，請你去看 item_model 裡那個「食譜設計局」(Base)
# 把它旗下所有的「食譜」(Models, 像 Item)
# 都透過「連線通道」(engine) 在資料庫裡「建立成真實的桌子」。
item_model.Base.metadata.create_all(bind=engine)
# --------------------

app = FastAPI()

# 載入路由
app.include_router(item.router, prefix="/api/v1/items", tags=["Items"])

@app.get("/")
def read_root():
    return {"Hello": "World"}