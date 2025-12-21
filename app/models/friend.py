# app/models/friend.py

from sqlalchemy import Column, Integer, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base

class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # 誰發起的
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False) # 加了誰
    status = Column(String, default="PENDING") # PENDING(申請中), ACCEPTED(已加好友)
    
    # 這裡只記錄ID即可，邏輯層處理顯示