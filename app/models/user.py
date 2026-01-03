# app/models/user.py

from sqlalchemy import Column, Integer, String, Boolean
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Integer, default=1000)
    
    pet_level = Column(Integer, default=1)
    pet_exp = Column(Integer, default=0)
    
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    attack = Column(Integer, default=10)
    
    pokemon_name = Column(String, default="皮卡丘")
    pokemon_image = Column(String, default="https://img.pokemondb.net/artwork/large/pikachu.jpg")
    active_pokemon_uid = Column(String, nullable=True) 
    
    pokemon_storage = Column(String, default="[]") 
    inventory = Column(String, default="{}")       
    unlocked_monsters = Column(String, default="") 
    
    quests = Column(String, default="[]")
    