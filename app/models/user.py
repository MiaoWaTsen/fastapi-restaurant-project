# app/models/user.py

from sqlalchemy import Column, Integer, String, Boolean
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # 玩家基礎數值
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=1000)
    
    # 寶可夢相關
    pet_level = Column(Integer, default=1)
    pet_exp = Column(Integer, default=0)
    
    # 戰鬥屬性 (會隨更換寶可夢改變)
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=10)
    
    # 寶可夢資料
    pokemon_name = Column(String, default="皮卡丘")
    pokemon_image = Column(String, default="https://img.pokemondb.net/artwork/large/pikachu.jpg")
    active_pokemon_uid = Column(String, nullable=True) 
    
    # 倉庫與背包 (JSON String)
    pokemon_storage = Column(String, default="[]") 
    inventory = Column(String, default="{}")       
    unlocked_monsters = Column(String, default="") 
    
    # 任務
    quests = Column(String, default="[]")
    
    # ❌ 移除 last_checkin_date，我們改存到 inventory 裡