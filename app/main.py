# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 🔥 1. 記得 import quest
from app.routers import auth, shop, social, quest 

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

# 🔥 2. 這一行非常重要！沒有這行就會出現 404 錯誤
app.include_router(quest.router, prefix="/api/v1/quests", tags=["quests"]) 

@app.get("/")
def read_root():
    return {"message": "Pokemon Battle Royale API is running!"}