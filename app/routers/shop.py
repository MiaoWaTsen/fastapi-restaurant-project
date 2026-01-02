# app/routers/shop.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import random
import json
import uuid

from app.db.session import get_db, engine
from app.common.deps import get_current_user
from app.models.user import User
from app.common.websocket import manager 

router = APIRouter()

# 0. 自動建立好友資料表
Base = declarative_base()

class Friendship(Base):
    __tablename__ = "friendships"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    friend_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="PENDING")

try:
    Friendship.__table__.create(bind=engine, checkfirst=True)
except:
    pass

# 全域變數
ONLINE_USERS = {}
INVITES = {}
DUEL_ROOMS = {}

def update_user_activity(user_id):
    ONLINE_USERS[user_id] = datetime.utcnow()

def is_user_busy(user_id):
    for room in DUEL_ROOMS.values():
        if (room["p1"] == user_id or room["p2"] == user_id) and room["status"] != "ENDED":
            return True
    return False

def get_now_tw():
    return datetime.utcnow() + timedelta(hours=8)

# =================================================================
# 1. 技能資料庫
# =================================================================
SKILL_DB = {
    "水槍": {"dmg": 16, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "撒嬌": {"dmg": 16, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "念力": {"dmg": 16, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "岩石封鎖": {"dmg": 16, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "毒針": {"dmg": 16, "effect": "buff_atk", "prob": 0.5, "val": 0.15, "desc": "50%加攻15%"},
    "藤鞭": {"dmg": 18, "effect": "buff_atk", "prob": 0.4, "val": 0.15, "desc": "40%加攻15%"},
    "火花": {"dmg": 18, "effect": "buff_atk", "prob": 0.4, "val": 0.15, "desc": "40%加攻15%"},
    "電光": {"dmg": 18, "effect": "buff_atk", "prob": 0.4, "val": 0.15, "desc": "40%加攻15%"},
    "挖洞": {"dmg": 18, "effect": "buff_atk", "prob": 0.4, "val": 0.15, "desc": "40%加攻15%"},
    "驚嚇": {"dmg": 18, "effect": "buff_atk", "prob": 0.4, "val": 0.15, "desc": "40%加攻15%"},
    "地震": {"dmg": 18, "effect": "heal", "prob": 0.4, "val": 0.15, "desc": "40%回血15%"},
    "冰礫": {"dmg": 18, "effect": "heal", "prob": 0.4, "val": 0.15, "desc": "40%回血15%"},
    "泥巴射擊": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "污泥炸彈": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "噴射火焰": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "水流噴射": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "精神強念": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "近身戰": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "電擊": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "龍息": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "撞擊": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "啄": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "緊束": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "葉刃": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "抓": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "放電": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "出奇一擊": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "毒擊": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "幻象光線": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "水流尾": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "燕返": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "龍尾": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "燒盡": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "種子炸彈": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "高速星星": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "泰山壓頂": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "大字爆炎": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "泥巴炸彈": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "冰凍光束": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "瘋狂伏特": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "雙倍奉還": {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "逆鱗": {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "暗影球": {"dmg": 34, "effect": "debuff_self", "prob": 1.0, "val": 0.1, "desc": "降自身10%攻"},
    "水砲": {"dmg": 34, "effect": "debuff_self", "prob": 1.0, "val": 0.1, "desc": "降自身10%攻"},
    "勇鳥猛攻": {"dmg": 34, "effect": "recoil", "prob": 1.0, "val": 0.15, "desc": "扣自身15%血"},
    "精神擊破": {"dmg": 30, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "神聖之火": {"dmg": 22, "effect": "buff_atk", "prob": 1.0, "val": 0.05, "desc": "100%加攻5%"},
    "氣旋攻擊": {"dmg": 22, "effect": "buff_atk", "prob": 1.0, "val": 0.05, "desc": "100%加攻5%"},
}

# =================================================================
# 2. 圖鑑資料庫
# =================================================================
POKEDEX_DATA = {
    # 關都野怪
    "小拉達": {"hp": 90, "atk": 80, "img": "https://img.pokemondb.net/artwork/large/rattata.jpg", "skills": ["抓", "出奇一擊", "撞擊"]},
    "波波": {"hp": 94, "atk": 84, "img": "https://img.pokemondb.net/artwork/large/pidgey.jpg", "skills": ["抓", "啄", "燕返"]},
    "烈雀": {"hp": 88, "atk": 92, "img": "https://img.pokemondb.net/artwork/large/spearow.jpg", "skills": ["抓", "啄", "燕返"]},
    "阿柏蛇": {"hp": 98, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/ekans.jpg", "skills": ["毒針", "毒擊", "緊束"]},
    "瓦斯彈": {"hp": 108, "atk": 100, "img": "https://img.pokemondb.net/artwork/large/koffing.jpg", "skills": ["毒針", "毒針", "撞擊"]},
    "海星星": {"hp": 120, "atk": 95, "img": "https://img.pokemondb.net/artwork/large/staryu.jpg", "skills": ["水槍", "幻象光線", "撞擊"]},
    "角金魚": {"hp": 125, "atk": 100, "img": "https://img.pokemondb.net/artwork/large/goldeen.jpg", "skills": ["水槍", "幻象光線", "泥巴射擊"]},
    "走路草": {"hp": 120, "atk": 110, "img": "https://img.pokemondb.net/artwork/large/oddish.jpg", "skills": ["種子炸彈", "撞擊", "毒擊"]},
    "穿山鼠": {"hp": 120, "atk": 110, "img": "https://img.pokemondb.net/artwork/large/sandshrew.jpg", "skills": ["抓", "泥巴射擊", "泥巴炸彈"]},
    "蚊香蝌蚪": {"hp": 122, "atk": 108, "img": "https://img.pokemondb.net/artwork/large/poliwag.jpg", "skills": ["雙倍奉還", "冰凍光束", "水槍"]},
    "小磁怪": {"hp": 120, "atk": 114, "img": "https://img.pokemondb.net/artwork/large/magnemite.jpg", "skills": ["電擊", "放電", "撞擊"]},
    "卡拉卡拉": {"hp": 120, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg", "skills": ["泥巴射擊", "泥巴炸彈", "挖洞"]},
    "喵喵": {"hp": 124, "atk": 124, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg", "skills": ["抓", "出奇一擊", "撞擊"]},
    "瑪瑙水母": {"hp": 130, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/tentacool.jpg", "skills": ["水槍", "水流尾", "緊束"]},
    "海刺龍": {"hp": 135, "atk": 135, "img": "https://img.pokemondb.net/artwork/large/seadra.jpg", "skills": ["水槍", "水流尾", "逆鱗"]},
    "電擊獸": {"hp": 135, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/electabuzz.jpg", "skills": ["電光", "電擊", "瘋狂伏特"]},
    "鴨嘴火獸": {"hp": 135, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/magmar.jpg", "skills": ["火花", "噴射火焰", "大字爆炎"]},
    "化石翼龍": {"hp": 140, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/aerodactyl.jpg", "skills": ["挖洞", "岩石封鎖", "勇鳥猛攻"]},
    "怪力": {"hp": 140, "atk": 145, "img": "https://img.pokemondb.net/artwork/large/machamp.jpg", "skills": ["雙倍奉還", "岩石封鎖", "近身戰"]},
    "暴鯉龍": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/gyarados.jpg", "skills": ["水槍", "水流尾", "勇鳥猛攻"]},

    "妙蛙種子": {"hp": 130, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg", "skills": ["藤鞭", "種子炸彈", "污泥炸彈"]},
    "小火龍": {"hp": 112, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg", "skills": ["火花", "噴射火焰", "大字爆炎"]},
    "傑尼龜": {"hp": 121, "atk": 121, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg", "skills": ["水槍", "水流噴射", "水流尾"]},
    
    "妙蛙花": {"hp": 142, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/venusaur.jpg", "skills": ["藤鞭", "種子炸彈", "污泥炸彈"]},
    "噴火龍": {"hp": 130, "atk": 142, "img": "https://img.pokemondb.net/artwork/large/charizard.jpg", "skills": ["火花", "噴射火焰", "大字爆炎"]},
    "水箭龜": {"hp": 136, "atk": 136, "img": "https://img.pokemondb.net/artwork/large/blastoise.jpg", "skills": ["水槍", "水流噴射", "水流尾"]},
    
    "毛辮羊": {"hp": 120, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg", "skills": ["撞擊", "撒嬌", "電擊"]},
    "皮卡丘": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg", "skills": ["電光", "放電", "電擊"]},
    "伊布": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg", "skills": ["撞擊", "挖洞", "高速星星"]},
    "六尾": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/vulpix.jpg", "skills": ["撞擊", "火花", "噴射火焰"]},
    "胖丁": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/jigglypuff.jpg", "skills": ["撞擊", "撒嬌", "精神強念"]},
    "皮皮": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/clefairy.jpg", "skills": ["撞擊", "撒嬌", "精神強念"]},
    "大蔥鴨": {"hp": 120, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg", "skills": ["啄", "葉刃", "勇鳥猛攻"]},
    "呆呆獸": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg", "skills": ["水槍", "幻象光線", "水流噴射"]},
    "可達鴨": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg", "skills": ["水槍", "幻象光線", "水流噴射"]},
    "耿鬼": {"hp": 96, "atk": 176, "img": "https://img.pokemondb.net/artwork/large/gengar.jpg", "skills": ["驚嚇", "污泥炸彈", "暗影球"]},
    "卡比獸": {"hp": 175, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/snorlax.jpg", "skills": ["泰山壓頂", "地震", "撞擊"]},
    "吉利蛋": {"hp": 220, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/chansey.jpg", "skills": ["抓", "精神強念", "撞擊"]},
    "幸福蛋": {"hp": 230, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/blissey.jpg", "skills": ["抓", "精神強念", "撞擊"]},
    
    "拉普拉斯": {"hp": 160, "atk": 138, "img": "https://img.pokemondb.net/artwork/large/lapras.jpg", "skills": ["水槍", "水流噴射", "冰凍光束"]},
    "快龍": {"hp": 144, "atk": 142, "img": "https://img.pokemondb.net/artwork/large/dragonite.jpg", "skills": ["龍息", "逆鱗", "勇鳥猛攻"]},
    
    "急凍鳥": {"hp": 145, "atk": 145, "img": "https://img.pokemondb.net/artwork/large/articuno.jpg", "skills": ["冰礫", "冰凍光束", "勇鳥猛攻"]},
    "火焰鳥": {"hp": 145, "atk": 145, "img": "https://img.pokemondb.net/artwork/large/moltres.jpg", "skills": ["噴射火焰", "大字爆炎", "勇鳥猛攻"]},
    "閃電鳥": {"hp": 145, "atk": 145, "img": "https://img.pokemondb.net/artwork/large/zapdos.jpg", "skills": ["電光", "瘋狂伏特", "勇鳥猛攻"]},
    "鳳王": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/ho-oh.jpg", "skills": ["燒盡", "勇鳥猛攻", "神聖之火"]},
    "洛奇亞": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/lugia.jpg", "skills": ["龍尾", "水砲", "氣旋攻擊"]},
    "超夢": {"hp": 152, "atk": 155, "img": "https://img.pokemondb.net/artwork/large/mewtwo.jpg", "skills": ["念力", "精神強念", "精神擊破"]},
    "夢幻": {"hp": 155, "atk": 152, "img": "https://img.pokemondb.net/artwork/large/mew.jpg", "skills": ["念力", "暗影球", "精神擊破"]},
}

COLLECTION_MONS = [
    "妙蛙種子", "小火龍", "傑尼龜", "妙蛙花", "噴火龍", "水箭龜",
    "毛辮羊", "皮卡丘", "伊布", "六尾", "胖丁", "皮皮", "大蔥鴨", "呆呆獸", "可達鴨",
    "耿鬼", "卡比獸", "吉利蛋", "幸福蛋", "拉普拉斯", "快龍",
    "急凍鳥", "火焰鳥", "閃電鳥", "超夢", "夢幻", "鳳王", "洛奇亞"
]

LEGENDARY_MONS = ["急凍鳥", "火焰鳥", "閃電鳥", "超夢", "夢幻", "鳳王", "洛奇亞"]
OBTAINABLE_MONS = [k for k in POKEDEX_DATA.keys()]

WILD_UNLOCK_LEVELS = {
    1: ["小拉達"], 6: ["波波"], 11: ["烈雀"], 16: ["阿柏蛇"], 21: ["瓦斯彈"],
    26: ["海星星"], 31: ["角金魚"], 36: ["走路草"], 41: ["穿山鼠"], 46: ["蚊香蝌蚪"],
    51: ["小磁怪"], 56: ["卡拉卡拉"], 61: ["喵喵"], 66: ["瑪瑙水母"], 71: ["海刺龍"],
    76: ["電擊獸"], 81: ["鴨嘴火獸"], 86: ["化石翼龍"], 91: ["怪力"], 96: ["暴鯉龍"]
}
GACHA_NORMAL = [{"name": "妙蛙種子", "rate": 5}, {"name": "小火龍", "rate": 5}, {"name": "傑尼龜", "rate": 5}, {"name": "六尾", "rate": 5}, {"name": "毛辮羊", "rate": 5}, {"name": "伊布", "rate": 10}, {"name": "皮卡丘", "rate": 10}, {"name": "皮皮", "rate": 10}, {"name": "胖丁", "rate": 10}, {"name": "大蔥鴨", "rate": 10}, {"name": "呆呆獸", "rate": 12.5}, {"name": "可達鴨", "rate": 12.5}]
GACHA_MEDIUM = [{"name": "妙蛙種子", "rate": 10}, {"name": "小火龍", "rate": 10}, {"name": "傑尼龜", "rate": 10}, {"name": "伊布", "rate": 10}, {"name": "皮卡丘", "rate": 10}, {"name": "呆呆獸", "rate": 10}, {"name": "可達鴨", "rate": 10}, {"name": "毛辮羊", "rate": 10}, {"name": "卡比獸", "rate": 5}, {"name": "吉利蛋", "rate": 3}, {"name": "拉普拉斯", "rate": 3}, {"name": "妙蛙花", "rate": 3}, {"name": "噴火龍", "rate": 3}, {"name": "水箭龜", "rate": 3}]
GACHA_HIGH = [{"name": "卡比獸", "rate": 20}, {"name": "吉利蛋", "rate": 20}, {"name": "幸福蛋", "rate": 10}, {"name": "拉普拉斯", "rate": 10}, {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10}, {"name": "快龍", "rate": 5}, {"name": "耿鬼", "rate": 5}]
GACHA_CANDY = [{"name": "伊布", "rate": 20}, {"name": "皮卡丘", "rate": 20}, {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10}, {"name": "卡比獸", "rate": 10}, {"name": "吉利蛋", "rate": 10}, {"name": "幸福蛋", "rate": 4}, {"name": "拉普拉斯", "rate": 3}, {"name": "快龍", "rate": 3}]
GACHA_GOLDEN = [{"name": "卡比獸", "rate": 30}, {"name": "吉利蛋", "rate": 35}, {"name": "幸福蛋", "rate": 20}, {"name": "拉普拉斯", "rate": 5}, {"name": "快龍", "rate": 5}, {"name": "耿鬼", "rate": 5}]
GACHA_LEGENDARY_CANDY = [{"name": "急凍鳥", "rate": 25}, {"name": "火焰鳥", "rate": 25}, {"name": "閃電鳥", "rate": 25}, {"name": "鳳王", "rate": 7.5}, {"name": "洛奇亞", "rate": 7.5}, {"name": "超夢", "rate": 5}, {"name": "夢幻", "rate": 5}]
GACHA_LEGENDARY_GOLD = [{"name": "快龍", "rate": 30}, {"name": "耿鬼", "rate": 20}, {"name": "急凍鳥", "rate": 15}, {"name": "火焰鳥", "rate": 15}, {"name": "閃電鳥", "rate": 15}, {"name": "鳳王", "rate": 2}, {"name": "洛奇亞", "rate": 2}, {"name": "超夢", "rate": 0.5}, {"name": "夢幻", "rate": 0.5}]

def create_xp_map():
    xp_map = { 1: 50, 2: 120, 3: 200, 4: 350, 5: 600, 6: 900, 7: 1360, 8: 1800, 9: 2300, 10: 2300 }
    current_req = 2300
    for lv in range(11, 51):
        current_req += 600
        xp_map[lv] = current_req
    for lv in range(51, 101):
        current_req += 2000
        xp_map[lv] = current_req
    return xp_map
LEVEL_XP_MAP = create_xp_map()
def get_req_xp(lv): return 999999999 if lv >= 100 else LEVEL_XP_MAP.get(lv, 999999)
def apply_iv_stats(base_val, iv, level, is_hp=False, is_player=True):
    iv_mult = 0.9 + (iv / 100) * 0.2
    growth_rate = (1.03 if is_hp else 1.031) if is_player else (1.033 if is_hp else 1.034)
    return int(base_val * iv_mult * (growth_rate ** (level - 1)))

# ... (RAID Logic 保持不變) ...
RAID_SCHEDULE = [(8, 0), (14, 0), (18, 0), (21, 0), (22, 0), (23, 0)] 
RAID_STATE = {"active": False, "status": "IDLE", "boss": None, "current_hp": 0, "max_hp": 0, "players": {}, "last_attack_time": None, "attack_counter": 0}
RAID_BOSS_POOL = [{"name": "❄️ 急凍鳥", "hp": 15000, "atk": 500, "img": "https://img.pokemondb.net/sprites/home/normal/articuno.png", "weight": 25}, {"name": "🔥 火焰鳥", "hp": 15000, "atk": 500, "img": "https://img.pokemondb.net/sprites/home/normal/moltres.png", "weight": 25}, {"name": "⚡ 閃電鳥", "hp": 15000, "atk": 500, "img": "https://img.pokemondb.net/sprites/home/normal/zapdos.png", "weight": 25}, {"name": "🔮 超夢", "hp": 20000, "atk": 800, "img": "https://img.pokemondb.net/sprites/home/normal/mewtwo.png", "weight": 5}, {"name": "✨ 夢幻", "hp": 20000, "atk": 800, "img": "https://img.pokemondb.net/sprites/home/normal/mew.png", "weight": 5}, {"name": "🌈 鳳王", "hp": 18000, "atk": 600, "img": "https://img.pokemondb.net/sprites/home/normal/ho-oh.png", "weight": 7.5}, {"name": "🌪️ 洛奇亞", "hp": 18000, "atk": 600, "img": "https://img.pokemondb.net/sprites/home/normal/lugia.png", "weight": 7.5}]

def update_raid_logic(db: Session = None):
    now = get_now_tw()
    curr_total_mins = now.hour * 60 + now.minute
    for (h, m) in RAID_SCHEDULE:
        start_total_mins = h * 60 + m
        start_lobby_mins = start_total_mins - 3 
        if start_lobby_mins < 0: start_lobby_mins += 1440
        if start_lobby_mins <= curr_total_mins < start_total_mins:
            if RAID_STATE["status"] != "LOBBY":
                boss_data = random.choices(RAID_BOSS_POOL, weights=[b['weight'] for b in RAID_BOSS_POOL], k=1)[0]
                RAID_STATE["active"] = True; RAID_STATE["status"] = "LOBBY"; RAID_STATE["boss"] = boss_data; RAID_STATE["max_hp"] = boss_data["hp"]; RAID_STATE["current_hp"] = boss_data["hp"]; RAID_STATE["players"] = {}; RAID_STATE["last_attack_time"] = get_now_tw(); RAID_STATE["attack_counter"] = 0
            return
    for (h, m) in RAID_SCHEDULE:
        start_total_mins = h * 60 + m
        if 0 <= (curr_total_mins - start_total_mins) < 15:
            if RAID_STATE["status"] == "LOBBY": RAID_STATE["status"] = "FIGHTING"; RAID_STATE["last_attack_time"] = get_now_tw()
            elif RAID_STATE["status"] == "IDLE": boss_data = random.choices(RAID_BOSS_POOL, weights=[b['weight'] for b in RAID_BOSS_POOL], k=1)[0]; RAID_STATE["active"] = True; RAID_STATE["status"] = "FIGHTING"; RAID_STATE["boss"] = boss_data; RAID_STATE["max_hp"] = boss_data["hp"]; RAID_STATE["current_hp"] = boss_data["hp"]; RAID_STATE["players"] = {}; RAID_STATE["last_attack_time"] = get_now_tw()
            if RAID_STATE["status"] == "FIGHTING":
                last_time = RAID_STATE.get("last_attack_time")
                if last_time and (get_now_tw() - last_time).total_seconds() >= 7:
                    if db:
                        RAID_STATE["last_attack_time"] = get_now_tw(); RAID_STATE["attack_counter"] += 1; base_dmg = int(RAID_STATE["boss"]["atk"] * 0.2); boss_dmg = int(base_dmg * random.uniform(0.95, 1.05))
                        active_uids = [uid for uid, p in RAID_STATE["players"].items() if not p.get("dead_at")]
                        if active_uids:
                            users_to_hit = db.query(User).filter(User.id.in_(active_uids)).all()
                            for u in users_to_hit:
                                u.hp = max(0, u.hp - boss_dmg)
                                if u.hp <= 0: RAID_STATE["players"][u.id]["dead_at"] = get_now_tw().isoformat()
                            db.commit()
            if RAID_STATE["current_hp"] <= 0: RAID_STATE["status"] = "ENDED"
            return
    if RAID_STATE["status"] != "IDLE": RAID_STATE["active"] = False; RAID_STATE["status"] = "IDLE"; RAID_STATE["boss"] = None

@router.get("/data/skills")
def get_skill_data(): return SKILL_DB

@router.get("/pokedex/all")
def get_all_pokedex():
    result = []
    for name, data in POKEDEX_DATA.items():
        is_obtainable = name in OBTAINABLE_MONS
        result.append({ "name": name, "img": data["img"], "hp": data["hp"], "atk": data["atk"], "is_obtainable": is_obtainable })
    return result

@router.get("/pokedex/collection")
def get_pokedex_collection(current_user: User = Depends(get_current_user)):
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    result = []
    for name in COLLECTION_MONS:
        if name in POKEDEX_DATA:
            data = POKEDEX_DATA[name]
            result.append({
                "name": name,
                "img": data["img"],
                "is_owned": name in unlocked
            })
    return result

@router.get("/wild/list")
def get_wild_list(level: int, current_user: User = Depends(get_current_user)):
    update_user_activity(current_user.id)
    if level > current_user.level: level = current_user.level
    unique_species = set()
    for lv in range(1, level + 1):
        if lv in WILD_UNLOCK_LEVELS:
            for name in WILD_UNLOCK_LEVELS[lv]: unique_species.add(name)
    if not unique_species: unique_species.add("小拉達")
    wild_list = []
    for name in unique_species:
        if name not in POKEDEX_DATA: continue
        base = POKEDEX_DATA[name]
        buffed_base_hp = int(base["hp"] * 1.3)
        buffed_base_atk = int(base["atk"] * 1.15)
        wild_hp = int(buffed_base_hp * (1.033 ** (level - 1)))
        wild_atk = int(buffed_base_atk * (1.034 ** (level - 1)))
        wild_skills = base.get("skills", ["撞擊", "撞擊", "撞擊"])
        wild_list.append({ "name": name, "raw_name": name, "is_powerful": False, "level": level, "hp": wild_hp, "max_hp": wild_hp, "attack": wild_atk, "image_url": base["img"], "skills": wild_skills })
    return wild_list

@router.post("/wild/attack")
async def wild_attack_api(is_win: bool = Query(...), is_powerful: bool = Query(False), target_name: str = Query("野怪"), target_level: int = Query(1), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    update_user_activity(current_user.id)
    current_user.hp = current_user.max_hp
    if is_win:
        target_data = POKEDEX_DATA.get(target_name, POKEDEX_DATA["小拉達"])
        base_stat_sum = target_data["hp"] + target_data["atk"]
        xp = int((base_stat_sum / 20) * target_level + 30)
        money = int(xp * 0.5) 
        current_user.exp += xp; current_user.pet_exp += xp; current_user.money += money
        msg = f"獲得 {xp} XP, {money} G"
        inv = json.loads(current_user.inventory)
        if random.random() < 0.4: inv["candy"] = inv.get("candy", 0) + 1; msg += " & 🍬 獲得神奇糖果!"
        if is_powerful: inv["growth_candy"] = inv.get("growth_candy", 0) + 1; msg += " & 🍬 成長糖果 x1"
        current_user.inventory = json.dumps(inv)
        
        # 🔥 V2.11.6: 更新任務進度 (擊敗野怪)
        quests = json.loads(current_user.quests) if current_user.quests else []
        quest_updated = False
        for q in quests:
            # 必須是 BATTLE_WILD 且目標名稱一致
            if q["type"] == "BATTLE_WILD" and q["status"] != "COMPLETED":
                # 模糊匹配 (例如任務目標是 '小拉達'，打倒 '🔥 強大的 小拉達' 也算)
                if q.get("target") in target_name: 
                    q["now"] += 1
                    quest_updated = True
        
        if quest_updated: current_user.quests = json.dumps(quests)
        
        req_xp_p = get_req_xp(current_user.level)
        while current_user.exp >= req_xp_p and current_user.level < 100: current_user.exp -= req_xp_p; current_user.level += 1; req_xp_p = get_req_xp(current_user.level); msg += f" | 訓練師升級 Lv.{current_user.level}!"
        req_xp_pet = get_req_xp(current_user.pet_level)
        pet_leveled_up = False
        while current_user.pet_exp >= req_xp_pet and current_user.pet_level < 100: current_user.pet_exp -= req_xp_pet; current_user.pet_level += 1; req_xp_pet = get_req_xp(current_user.pet_level); pet_leveled_up = True; msg += f" | 寶可夢升級 Lv.{current_user.pet_level}!"
        box = json.loads(current_user.pokemon_storage)
        active_pet = next((p for p in box if p['uid'] == current_user.active_pokemon_uid), None)
        if active_pet:
            active_pet["exp"] = current_user.pet_exp; active_pet["lv"] = current_user.pet_level
            if pet_leveled_up:
                base = POKEDEX_DATA.get(active_pet["name"])
                if base: current_user.max_hp = apply_iv_stats(base["hp"], active_pet["iv"], current_user.pet_level, is_hp=True, is_player=True); current_user.attack = apply_iv_stats(base["atk"], active_pet["iv"], current_user.pet_level, is_hp=False, is_player=True); current_user.hp = current_user.max_hp
        current_user.pokemon_storage = json.dumps(box)
        db.commit()
        return {"message": f"勝利！HP已回復。{msg}"}
    db.commit()
    return {"message": "戰鬥結束，HP已回復。"}

@router.post("/gacha/{gacha_type}")
async def play_gacha(gacha_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try: box = json.loads(current_user.pokemon_storage) if current_user.pokemon_storage else []
    except: box = []
    if len(box) >= 25: raise HTTPException(status_code=400, detail="盒子滿了！請先放生")
    try: inventory = json.loads(current_user.inventory) if current_user.inventory else {}
    except: inventory = {}
    cost = 0; pool = []
    if gacha_type == 'normal': pool = GACHA_NORMAL; cost = 1500
    elif gacha_type == 'medium': pool = GACHA_MEDIUM; cost = 3000
    elif gacha_type == 'high': pool = GACHA_HIGH; cost = 10000
    elif gacha_type == 'candy': pool = GACHA_CANDY; cost = 12
    elif gacha_type == 'golden': pool = GACHA_GOLDEN; cost = 3
    elif gacha_type == 'legendary_candy': pool = GACHA_LEGENDARY_CANDY; cost = 5
    elif gacha_type == 'legendary_gold': pool = GACHA_LEGENDARY_GOLD; cost = 400000
    else: raise HTTPException(status_code=400, detail="未知類型")
    
    if gacha_type == 'candy':
        if inventory.get("candy", 0) < cost: raise HTTPException(status_code=400, detail="糖果不足")
        inventory["candy"] -= cost
    elif gacha_type == 'golden':
        if inventory.get("golden_candy", 0) < cost: raise HTTPException(status_code=400, detail="黃金糖果不足")
        inventory["golden_candy"] -= cost
    elif gacha_type == 'legendary_candy':
        if inventory.get("legendary_candy", 0) < cost: raise HTTPException(status_code=400, detail="傳說糖果不足")
        inventory["legendary_candy"] -= cost
    else:
        if current_user.money < cost: raise HTTPException(status_code=400, detail="金幣不足")
        current_user.money -= cost
        
    total_rate = sum(p["rate"] for p in pool); r = random.uniform(0, total_rate); acc = 0; prize_name = pool[0]["name"]
    for p in pool:
        acc += p["rate"]
        if r <= acc: prize_name = p["name"]; break
    
    new_lv = random.randint(1, current_user.level)
    if 'legendary' in gacha_type: iv = random.randint(60, 100)
    else: iv = int(random.triangular(0, 100, 50))
    
    new_mon = { "uid": str(uuid.uuid4()), "name": prize_name, "iv": iv, "lv": new_lv, "exp": 0 }
    box.append(new_mon)
    current_user.pokemon_storage = json.dumps(box); current_user.inventory = json.dumps(inventory)
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    if prize_name not in unlocked: unlocked.append(prize_name); current_user.unlocked_monsters = ",".join(unlocked)
    
    # 🔥 V2.11.6: 移除 Gacha 任務邏輯，現在只剩戰鬥任務
    db.commit()
    try:
        if 'legendary' in gacha_type or gacha_type in ['golden', 'high'] or prize_name in ['快龍', '超夢', '夢幻', '拉普拉斯', '幸福蛋', '耿鬼', '鳳王', '洛奇亞']: await manager.broadcast(f"🎰 恭喜 [{current_user.username}] 獲得了稀有的 [{prize_name}] (Lv.{new_lv})！")
    except: pass
    return {"message": f"獲得 {prize_name} (Lv.{new_lv}, IV: {iv})!", "prize": new_mon, "user": current_user}

@router.post("/box/swap/{pokemon_uid}")
async def swap_active_pokemon(pokemon_uid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage); target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到")
    current_user.active_pokemon_uid = pokemon_uid; current_user.pokemon_name = target["name"]
    base = POKEDEX_DATA.get(target["name"])
    current_user.pokemon_image = base["img"] if base else "https://via.placeholder.com/150"
    current_user.pet_level = target["lv"]; current_user.pet_exp = target["exp"]
    if base: current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], is_hp=True, is_player=True); current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], is_hp=False, is_player=True)
    else: current_user.max_hp = 100; current_user.attack = 10
    current_user.hp = current_user.max_hp
    db.commit()
    await manager.broadcast(f"EVENT:PVP_SWAP|{current_user.id}")
    return {"message": f"就決定是你了，{target['name']}！"}

@router.post("/box/action/{action}/{pokemon_uid}")
async def box_action(action: str, pokemon_uid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage); inv = json.loads(current_user.inventory)
    target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到")
    if action == "release":
        if pokemon_uid == current_user.active_pokemon_uid: raise HTTPException(status_code=400, detail="出戰中無法放生")
        box = [p for p in box if p["uid"] != pokemon_uid]
        if target["name"] in LEGENDARY_MONS: inv["legendary_candy"] = inv.get("legendary_candy", 0) + 1; msg = "✨ 放生傳說寶可夢，獲得 🔮 傳說糖果 x1"
        else: current_user.money += 100; msg = "放生成功，獲得 100 Gold"
    elif action == "candy":
        if target["lv"] >= current_user.level: raise HTTPException(status_code=400, detail=f"等級已達上限 (訓練師 Lv.{current_user.level})")
        if inv.get("growth_candy", 0) < 1: raise HTTPException(status_code=400, detail="成長糖果不足")
        inv["growth_candy"] -= 1; target["exp"] += 1000
        req = get_req_xp(target["lv"])
        while target["exp"] >= req and target["lv"] < 100:
            if target["lv"] >= current_user.level: break
            target["lv"] += 1; target["exp"] -= req; req = get_req_xp(target["lv"])
        if pokemon_uid == current_user.active_pokemon_uid:
            base = POKEDEX_DATA.get(target["name"])
            if base: current_user.pet_level = target["lv"]; current_user.pet_exp = target["exp"]; current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], is_hp=True, is_player=True); current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], is_hp=False, is_player=True)
        msg = f"使用成長糖果，經驗+1000 (Lv.{target['lv']})"
    current_user.pokemon_storage = json.dumps(box); current_user.inventory = json.dumps(inv)
    db.commit()
    return {"message": msg, "user": current_user}

@router.post("/gamble")
async def gamble(amount: int = Query(..., gt=0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < amount: raise HTTPException(status_code=400, detail="金幣不足")
    if random.random() < 0.5: current_user.money += amount; msg = f"🎰 贏了！獲得 {amount} Gold！"
    else: current_user.money -= amount; msg = "💸 輸了... 沒關係下次再來！"
    db.commit()
    return {"message": msg, "money": current_user.money}

@router.post("/heal")
async def buy_heal(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 50: raise HTTPException(status_code=400, detail="金幣不足")
    current_user.money -= 50; current_user.hp = current_user.max_hp; db.commit()
    return {"message": "體力已補滿"}

@router.post("/social/invite/{target_id}")
def invite_player(target_id: int, current_user: User = Depends(get_current_user)):
    if is_user_busy(target_id): raise HTTPException(status_code=400, detail="對方正在戰鬥中")
    INVITES[target_id] = current_user.id
    return {"message": "邀請已發送"}

@router.get("/social/check_invite")
def check_invite(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    source_id = INVITES.get(current_user.id)
    if source_id:
        source_user = db.query(User).filter(User.id == source_id).first()
        if source_user: return {"has_invite": True, "source_id": source_id, "source_name": source_user.username}
    return {"has_invite": False}

@router.post("/social/accept_invite/{source_id}")
def accept_invite(source_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if INVITES.get(current_user.id) != source_id: raise HTTPException(status_code=400, detail="邀請已失效")
    room_id = str(uuid.uuid4())
    DUEL_ROOMS[room_id] = {
        "p1": source_id, "p2": current_user.id, "status": "PREPARING",
        "start_time": datetime.utcnow().isoformat(),
        "countdown_end": (datetime.utcnow() + timedelta(seconds=12)).isoformat(),
        "turn": None, "p1_data": None, "p2_data": None,
        "ended_at": None 
    }
    del INVITES[current_user.id]
    return {"message": "接受成功", "room_id": room_id}

@router.post("/social/reject_invite/{source_id}")
def reject_invite(source_id: int, current_user: User = Depends(get_current_user)):
    if INVITES.get(current_user.id) == source_id: del INVITES[current_user.id]
    return {"message": "已拒絕"}

@router.get("/duel/status")
def check_duel_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_user_activity(current_user.id)
    now = datetime.utcnow()
    keys_to_del = []
    for rid, r in DUEL_ROOMS.items():
        if r.get("ended_at") and (now - datetime.fromisoformat(r["ended_at"])).total_seconds() > 60:
            keys_to_del.append(rid)
    for k in keys_to_del: del DUEL_ROOMS[k]

    my_room_id = None; room = None
    for rid, r in DUEL_ROOMS.items():
        if r["p1"] == current_user.id or r["p2"] == current_user.id:
            my_room_id = rid; room = r; break
            
    if not room: return {"status": "NONE"}
    
    if room["status"] == "PREPARING":
        end_time = datetime.fromisoformat(room["countdown_end"])
        remaining = (end_time - now).total_seconds()
        if remaining <= 0:
            p1 = db.query(User).filter(User.id == room["p1"]).first()
            p2 = db.query(User).filter(User.id == room["p2"]).first()
            first_turn = p1.id
            if p1.pet_level < p2.pet_level: first_turn = p1.id
            elif p2.pet_level < p1.pet_level: first_turn = p2.id
            else:
                if p1.attack > p2.attack: first_turn = p1.id
                elif p2.attack > p1.attack: first_turn = p2.id
                else: first_turn = random.choice([p1.id, p2.id])
            room["status"] = "FIGHTING"; room["turn"] = first_turn
            room["p1_data"] = {"id": p1.id, "name": p1.username, "hp": p1.hp, "max_hp": p1.max_hp, "atk": p1.attack, "img": p1.pokemon_image, "pname": p1.pokemon_name}
            room["p2_data"] = {"id": p2.id, "name": p2.username, "hp": p2.hp, "max_hp": p2.max_hp, "atk": p2.attack, "img": p2.pokemon_image, "pname": p2.pokemon_name}
            return {"status": "FIGHTING", "room": room}
        else: return {"status": "PREPARING", "remaining": remaining}
    return {"status": room["status"], "room": room}

@router.post("/duel/attack")
def duel_attack(damage: int = Query(0), heal: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    room = None
    for r in DUEL_ROOMS.values():
        if (r["p1"] == current_user.id or r["p2"] == current_user.id) and r["status"] == "FIGHTING":
            room = r; break
    if not room: raise HTTPException(status_code=400, detail="不在對戰中")
    if room["turn"] != current_user.id: raise HTTPException(status_code=400, detail="還沒輪到你")
    
    is_p1 = (current_user.id == room["p1"])
    target_key = "p2_data" if is_p1 else "p1_data"
    target_id = room["p2"] if is_p1 else room["p1"]
    my_key = "p1_data" if is_p1 else "p2_data"
    
    target_user = db.query(User).filter(User.id == target_id).first()
    room[target_key]["hp"] = max(0, room[target_key]["hp"] - damage)
    target_user.hp = room[target_key]["hp"]
    
    if heal > 0:
        room[my_key]["hp"] = min(room[my_key]["max_hp"], room[my_key]["hp"] + heal)
        current_user.hp = room[my_key]["hp"]
        
    if room[target_key]["hp"] <= 0:
        room["status"] = "ENDED"
        room["ended_at"] = datetime.utcnow().isoformat() 
        current_user.money += 300; current_user.exp += 500
        current_user.hp = current_user.max_hp
        target_user.hp = target_user.max_hp
        db.commit()
        return {"result": "WIN", "reward": "獲得 300G & 500 XP"}
        
    room["turn"] = target_id
    db.commit()
    return {"result": "NEXT", "damage": damage, "heal": heal}

@router.get("/raid/status")
def get_raid_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_raid_logic(db)
    my_status = {}
    if current_user.id in RAID_STATE["players"]:
        my_status = RAID_STATE["players"][current_user.id]
        
    return {
        "active": RAID_STATE["active"],
        "status": RAID_STATE["status"],
        "boss_name": RAID_STATE["boss"]["name"] if RAID_STATE["boss"] else "",
        "hp": RAID_STATE["current_hp"],
        "max_hp": RAID_STATE["max_hp"],
        "image": RAID_STATE["boss"]["img"] if RAID_STATE["boss"] else "",
        "my_status": my_status,
        "user_hp": current_user.hp
    }

@router.post("/raid/join")
def join_raid(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_raid_logic(db)
    if RAID_STATE["status"] == "LOBBY": return {"message": "戰鬥尚未開始，請稍候..."}
    if RAID_STATE["status"] != "FIGHTING": raise HTTPException(status_code=400, detail="目前戰鬥尚未開始")
    if current_user.id in RAID_STATE["players"]: return {"message": "已經加入過了"}
    if current_user.money < 1000: raise HTTPException(status_code=400, detail="金幣不足 (需 1000 G)")
    current_user.money -= 1000
    RAID_STATE["players"][current_user.id] = { "name": current_user.username, "dmg": 0, "dead_at": None, "claimed": False }
    db.commit()
    return {"message": "成功加入團體戰！"}

@router.post("/raid/attack")
def attack_raid_boss(damage: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_raid_logic(db)
    if current_user.id not in RAID_STATE["players"]: raise HTTPException(status_code=400, detail="你不在大廳中")
    p_data = RAID_STATE["players"][current_user.id]
    if p_data.get("dead_at"): raise HTTPException(status_code=400, detail="你已死亡，請盡快復活！")
    if RAID_STATE["status"] != "FIGHTING": return {"message": "戰鬥尚未開始或已結束", "boss_hp": RAID_STATE["current_hp"]}
    RAID_STATE["current_hp"] = max(0, RAID_STATE["current_hp"] - damage)
    return {"message": f"造成 {damage} 點傷害", "boss_hp": RAID_STATE["current_hp"]}

@router.post("/raid/recover")
def raid_recover(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    heal_amount = int(current_user.max_hp * 0.2)
    current_user.hp = min(current_user.max_hp, current_user.hp + heal_amount)
    db.commit()
    return {"message": f"回復了 {heal_amount} HP", "hp": current_user.hp}

@router.post("/raid/revive")
def revive_raid(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id not in RAID_STATE["players"]: raise HTTPException(status_code=400, detail="你不在大廳中")
    if current_user.money < 500: raise HTTPException(status_code=400, detail="金幣不足 500G")
    current_user.money -= 500
    RAID_STATE["players"][current_user.id]["dead_at"] = None
    current_user.hp = current_user.max_hp
    db.commit()
    return {"message": "復活成功！"}

@router.post("/raid/claim")
def claim_raid_reward(choice: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if RAID_STATE["status"] != "ENDED": raise HTTPException(status_code=400, detail="戰鬥尚未結束")
    if current_user.id not in RAID_STATE["players"]: raise HTTPException(status_code=400, detail="你沒有參與這場戰鬥")
    p_data = RAID_STATE["players"][current_user.id]
    if p_data.get("claimed"): return {"message": "已經領過獎勵了"}
    
    # 🔥 V2.11.7: 團體戰獎勵權重調整 (20% Boss / 40% Candy / 40% Money)
    weights = [20, 40, 40]
    options = ["pet", "candy", "money"]
    prize = random.choices(options, weights=weights, k=1)[0]
    
    msg = ""
    inv = json.loads(current_user.inventory)
    if prize == "candy":
        inv["legendary_candy"] = inv.get("legendary_candy", 0) + 1
        msg = "獲得 🔮 傳說糖果 x1"
    elif prize == "money":
        current_user.money += 6000
        msg = "獲得 💰 6000 Gold"
    elif prize == "pet":
        boss_name = RAID_STATE["boss"]["name"].split(" ")[1] 
        new_lv = random.randint(1, current_user.level)
        new_mon = { "uid": str(uuid.uuid4()), "name": boss_name, "iv": int(random.randint(60, 100)), "lv": new_lv, "exp": 0 }
        try:
            box = json.loads(current_user.pokemon_storage)
            box.append(new_mon)
            current_user.pokemon_storage = json.dumps(box)
            msg = f"獲得 Boss 寶可夢：{boss_name} (Lv.{new_lv})！"
        except:
            msg = "背包滿了，獲得 6000G 代替"
            current_user.money += 6000

    RAID_STATE["players"][current_user.id]["claimed"] = True
    current_user.inventory = json.dumps(inv)
    current_user.exp += 3000; current_user.pet_exp += 3000
    current_user.hp = current_user.max_hp 
    db.commit()
    return {"message": msg, "prize": prize}

@router.post("/social/daily_checkin")
def daily_checkin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = get_now_tw()
    today_str = now.strftime("%Y-%m-%d")
    if current_user.last_checkin_date == today_str: return {"message": "今天已經簽到過了"}
    prizes = ["1500G", "3000G", "candy", "golden", "8000G", "legendary"]
    weights = [30, 20, 20, 20, 6, 4]
    result = random.choices(prizes, weights=weights, k=1)[0]
    
    # 🔥 V2.11.7: 簽到防呆修復
    try:
        if not current_user.inventory:
            inv = {}
        else:
            inv = json.loads(current_user.inventory)
    except:
        inv = {}
        
    msg = ""
    if result == "1500G": current_user.money += 1500; msg = "獲得 1500 Gold"
    elif result == "3000G": current_user.money += 3000; msg = "獲得 3000 Gold"
    elif result == "candy": inv["candy"] = inv.get("candy", 0) + 5; msg = "獲得 🍬 神奇糖果 x5"
    elif result == "golden": inv["golden_candy"] = inv.get("golden_candy", 0) + 1; msg = "獲得 ✨ 黃金糖果 x1"
    elif result == "8000G": current_user.money += 8000; msg = "大獎！獲得 💰 8000 Gold"
    elif result == "legendary": inv["legendary_candy"] = inv.get("legendary_candy", 0) + 1; msg = "超級大獎！獲得 🔮 傳說糖果 x1"
    current_user.last_checkin_date = today_str
    current_user.inventory = json.dumps(inv)
    db.commit()
    return {"message": f"簽到成功！{msg}"}

@router.post("/social/add/{target_id}")
def add_friend(target_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if target_id == current_user.id: raise HTTPException(status_code=400, detail="不能加自己")
    target_user = db.query(User).filter(User.id == target_id).first()
    if not target_user: raise HTTPException(status_code=404, detail="找不到該玩家 ID") 
    existing = db.query(Friendship).filter(or_((Friendship.user_id == current_user.id) & (Friendship.friend_id == target_id), (Friendship.user_id == target_id) & (Friendship.friend_id == current_user.id))).first()
    if existing: return {"message": "已經是好友或已發送邀請"}
    new_fs = Friendship(user_id=current_user.id, friend_id=target_id, status="PENDING")
    db.add(new_fs); db.commit()
    return {"message": "已發送好友邀請"}

@router.get("/social/requests")
def get_friend_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reqs = db.query(Friendship).filter(Friendship.friend_id == current_user.id, Friendship.status == "PENDING").all()
    result = []
    for r in reqs:
        sender = db.query(User).filter(User.id == r.user_id).first()
        if sender: result.append({"request_id": r.id, "username": sender.username, "pokemon_image": sender.pokemon_image})
    return result

@router.post("/social/accept/{req_id}")
def accept_friend(req_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fs = db.query(Friendship).filter(Friendship.id == req_id, Friendship.friend_id == current_user.id).first()
    if not fs: raise HTTPException(status_code=404, detail="找不到邀請")
    fs.status = "ACCEPTED"
    db.commit()
    return {"message": "已接受好友"}

@router.post("/social/reject/{req_id}")
def reject_friend_request(req_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fs = db.query(Friendship).filter(Friendship.id == req_id, Friendship.friend_id == current_user.id).first()
    if not fs: raise HTTPException(status_code=404, detail="找不到邀請")
    db.delete(fs)
    db.commit()
    return {"message": "已拒絕"}

@router.post("/social/remove/{friend_id}")
def remove_friend(friend_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fs = db.query(Friendship).filter(
        or_(
            (Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id),
            (Friendship.user_id == friend_id) & (Friendship.friend_id == current_user.id)
        )
    ).first()
    if not fs: raise HTTPException(status_code=404, detail="你們不是好友")
    db.delete(fs)
    db.commit()
    return {"message": "已刪除好友"}

@router.get("/social/list")
def get_friend_list(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friends_query = db.query(Friendship).filter(or_(Friendship.user_id == current_user.id, Friendship.friend_id == current_user.id), Friendship.status == "ACCEPTED").all()
    result = []
    for f in friends_query:
        target_id = f.friend_id if f.user_id == current_user.id else f.user_id
        target = db.query(User).filter(User.id == target_id).first()
        if target: result.append({"id": target.id, "username": target.username, "pokemon_image": target.pokemon_image, "can_gift": True})
    return result

@router.get("/social/players")
def get_online_players(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_user_activity(current_user.id)
    all_users = db.query(User).all()
    result = []
    now = datetime.utcnow()
    for u in all_users:
        last_seen = ONLINE_USERS.get(u.id)
        is_online = False
        if last_seen and (now - last_seen).total_seconds() < 30: is_online = True
        result.append({ "id": u.id, "username": u.username, "pokemon_image": u.pokemon_image, "is_online": is_online })
    return result

@router.post("/social/redeem")
def redeem_code(code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try: inv = json.loads(current_user.inventory) if current_user.inventory else {}
    except: inv = {}
    if "redeemed_codes" not in inv: inv["redeemed_codes"] = []
    code = code.strip()
    if code in inv["redeemed_codes"]: raise HTTPException(status_code=400, detail="此序號已經使用過了！")
    msg = ""; success = False
    if code == "1PF563GFK2":
        inv["legendary_candy"] = inv.get("legendary_candy", 0) + 10
        msg = "兌換成功！獲得 🔮 傳說糖果 x10"; success = True
    else: raise HTTPException(status_code=400, detail="無效的序號")
    if success:
        inv["redeemed_codes"].append(code)
        current_user.inventory = json.dumps(inv)
        db.commit()
        return {"message": msg, "user": current_user}

@router.delete("/admin/delete_user")
def delete_user_by_name(username: str, db: Session = Depends(get_db)):
    target = db.query(User).filter(User.username == username).first()
    if not target: raise HTTPException(status_code=404, detail=f"找不到名為 [{username}] 的玩家")
    uid = target.id
    if uid in ONLINE_USERS: del ONLINE_USERS[uid]
    if uid in INVITES: del INVITES[uid]
    keys_to_del = [k for k, v in INVITES.items() if v == uid]
    for k in keys_to_del: del INVITES[k]
    rooms_to_del = []
    for rid, r in DUEL_ROOMS.items():
        if r["p1"] == uid or r["p2"] == uid: rooms_to_del.append(rid)
    for rid in rooms_to_del: del DUEL_ROOMS[rid]
    if uid in RAID_STATE["players"]: del RAID_STATE["players"][uid]
    try:
        db.query(Friendship).filter(or_(Friendship.user_id == uid, Friendship.friend_id == uid)).delete()
        db.delete(target)
        db.commit()
        return {"message": f"✅ 已成功刪除玩家 [{username}] 及其所有資料"}
    except Exception as e:
        db.rollback()
        return {"message": f"❌ 刪除失敗 (資料庫錯誤): {str(e)}"}