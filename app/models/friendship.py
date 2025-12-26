from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id")) # 發送邀請的人
    accepter_id = Column(Integer, ForeignKey("users.id"))  # 接收邀請的人
    is_accepted = Column(Boolean, default=False)           # False=申請中, True=已是好友

    # 關聯
    requester = relationship("User", foreign_keys=[requester_id])
    accepter = relationship("User", foreign_keys=[accepter_id])