# app/models/friend.py

from sqlalchemy import Column, Integer, ForeignKey, String
from app.models.base import Base

class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True)
    
    # 🔥 修正：指向新的 users_v11 表格
    user_id = Column(Integer, ForeignKey("users_v11.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users_v11.id"), nullable=False)
    
    status = Column(String(20), default="PENDING")