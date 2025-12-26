# app/models/friendship.py

from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    
    # 🔥 重點：改成 users_v11.id
    requester_id = Column(Integer, ForeignKey("users_v11.id")) 
    accepter_id = Column(Integer, ForeignKey("users_v11.id"))
    
    is_accepted = Column(Boolean, default=False)

    requester = relationship("User", foreign_keys=[requester_id])
    accepter = relationship("User", foreign_keys=[accepter_id])