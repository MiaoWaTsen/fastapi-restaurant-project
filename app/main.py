# app/main.py
from fastapi import FastAPI
from app.routers import items # 假設你的路由檔名叫 items.py

app = FastAPI()

# 載入路由，並加上 prefix
app.include_router(items.router, prefix="/api/v1/items", tags=["Items"])

@app.get("/")
def read_root():
    return {"Hello": "World"}