# app/models/gift.py

from sqlalchemy import Column, Integer, ForeignKey, String, Date
from app.models.base import Base
from datetime import datetime

class Gift(Base):
    __tablename__ = "gifts"

    id = Column(Integer, primary_key=True, index=True)
    # 🔥 修正：指向新的 users_v11 表格
    sender_id = Column(Integer, ForeignKey("users_v11.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users_v11.id"), nullable=False)
    sender_name = Column(String(50), default="Unknown")
    
class GiftCooldown(Base):
    __tablename__ = "gift_cooldowns"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, index=True)
    receiver_id = Column(Integer, index=True)
    last_sent_date = Column(Date, default=datetime.utcnow().date)