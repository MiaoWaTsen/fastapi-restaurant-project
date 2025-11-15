# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 從你剛剛建立的 config.py 匯入 settings
from app.core.config import settings 

engine = create_engine(
    # 使用 settings.DATABASE_URL 來取代寫死的字串
    settings.DATABASE_URL, 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()