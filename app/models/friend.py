# app/models/friend.py

from sqlalchemy import Column, Integer, ForeignKey, String
from app.models.base import Base

class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True)
    
    # 🔥 修正：這裡必須指向 "users_v9.id"，否則會報錯說找不到表格 🔥
    user_id = Column(Integer, ForeignKey("users_v9.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users_v9.id"), nullable=False)
    
    status = Column(String, default="PENDING")