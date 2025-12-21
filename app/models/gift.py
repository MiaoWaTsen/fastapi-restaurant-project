# app/models/gift.py

from sqlalchemy import Column, Integer, ForeignKey, String, Date
from app.models.base import Base
from datetime import datetime

# 記錄待領取的禮物
class Gift(Base):
    __tablename__ = "gifts"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users_v9.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users_v9.id"), nullable=False)
    sender_name = Column(String, default="Unknown")
    
# 記錄送禮冷卻時間 (每天每對好友只能送一次)
class GiftCooldown(Base):
    __tablename__ = "gift_cooldowns"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, index=True)
    receiver_id = Column(Integer, index=True)
    last_sent_date = Column(Date, default=datetime.utcnow().date)