# app/routers/shop.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import json
import uuid

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.common.websocket import manager 

router = APIRouter()

# =================================================================
# 1. 技能資料庫 (SKILL_DB) - V2.6.0 平衡調整
# =================================================================
SKILL_DB = {
    # [16傷害區 - 50% 機率特效]
    "水槍":     {"dmg": 16, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "撒嬌":     {"dmg": 16, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "念力":     {"dmg": 16, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "岩石封鎖": {"dmg": 16, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "毒針":     {"dmg": 16, "effect": "buff_atk", "prob": 0.5, "val": 0.15, "desc": "50%加攻15%"},

    # [18傷害區 - 35% 機率特效]
    "藤鞭":     {"dmg": 18, "effect": "buff_atk", "prob": 0.35, "val": 0.15, "desc": "35%加攻15%"},
    "火花":     {"dmg": 18, "effect": "buff_atk", "prob": 0.35, "val": 0.15, "desc": "35%加攻15%"},
    "電光":     {"dmg": 18, "effect": "buff_atk", "prob": 0.35, "val": 0.15, "desc": "35%加攻15%"},
    "挖洞":     {"dmg": 18, "effect": "buff_atk", "prob": 0.35, "val": 0.15, "desc": "35%加攻15%"},
    "驚嚇":     {"dmg": 18, "effect": "buff_atk", "prob": 0.35, "val": 0.15, "desc": "35%加攻15%"},
    "地震":     {"dmg": 18, "effect": "heal", "prob": 0.35, "val": 0.15, "desc": "35%回血15%"},
    "冰礫":     {"dmg": 18, "effect": "heal", "prob": 0.35, "val": 0.15, "desc": "35%回血15%"},

    # [20傷害區 - 30% 機率特效]
    "泥巴射擊": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "污泥炸彈": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "噴射火焰": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "水流噴射": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "精神強念": {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "近身戰":   {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},
    "電擊":     {"dmg": 20, "effect": "buff_atk", "prob": 0.3, "val": 0.15, "desc": "30%加攻15%"},

    # [24傷害區 - 無特效]
    "撞擊": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "啄":   {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "緊束": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "葉刃": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},

    # [26傷害區 - 無特效]
    "抓":       {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "放電":     {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "出奇一擊": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "毒擊":     {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "幻象光線": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "水流尾":   {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "燕返":     {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "種子炸彈": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "高速星星": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "泰山壓頂": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "大字爆炎": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "泥巴炸彈": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "冰凍光束": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "瘋狂伏特": {"dmg": 26, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},

    # [28傷害區 - 無特效]
    "雙倍奉還": {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "逆鱗":     {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "精神撃破": {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "破壞光線": {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},

    # [34傷害區 - 強力副作用]
    # 🔥 修正：暗影球降自身攻擊 🔥
    "暗影球":   {"dmg": 34, "effect": "debuff_self", "prob": 1.0, "val": 0.1, "desc": "降自身10%攻"},
    "勇鳥猛攻": {"dmg": 34, "effect": "recoil", "prob": 1.0, "val": 0.15, "desc": "扣自身15%血"}
}

# =================================================================
# 2. 完整圖鑑資料庫 (POKEDEX_DATA)
# =================================================================
POKEDEX_DATA = {
    # --- 野怪區 ---
    "小拉達": {"hp": 90, "atk": 80, "img": "https://img.pokemondb.net/artwork/large/rattata.jpg", "skills": ["抓", "出奇一擊", "撞擊"]},
    "波波":   {"hp": 94, "atk": 84, "img": "https://img.pokemondb.net/artwork/large/pidgey.jpg", "skills": ["抓", "啄", "燕返"]},
    "烈雀":   {"hp": 88, "atk": 92, "img": "https://img.pokemondb.net/artwork/large/spearow.jpg", "skills": ["抓", "啄", "燕返"]},
    "阿柏蛇": {"hp": 98, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/ekans.jpg", "skills": ["毒針", "毒擊", "緊束"]},
    "瓦斯彈": {"hp": 108, "atk": 100, "img": "https://img.pokemondb.net/artwork/large/koffing.jpg", "skills": ["毒針", "毒針", "撞擊"]},
    "海星星": {"hp": 120, "atk": 95, "img": "https://img.pokemondb.net/artwork/large/staryu.jpg", "skills": ["水槍", "幻象光線", "撞擊"]},
    "角金魚": {"hp": 125, "atk": 100, "img": "https://img.pokemondb.net/artwork/large/goldeen.jpg", "skills": ["水槍", "幻象光線", "泥巴射擊"]},
    "走路草": {"hp": 120, "atk": 110, "img": "https://img.pokemondb.net/artwork/large/oddish.jpg", "skills": ["種子炸彈", "撞擊", "毒擊"]},
    "穿山鼠": {"hp": 120, "atk": 110, "img": "https://img.pokemondb.net/artwork/large/sandshrew.jpg", "skills": ["抓", "泥巴射擊", "泥巴炸彈"]},
    "蚊香蝌蚪": {"hp": 122, "atk": 108, "img": "https://img.pokemondb.net/artwork/large/poliwag.jpg", "skills": ["雙倍奉還", "冰凍光束", "水槍"]},
    "小磁怪": {"hp": 120, "atk": 114, "img": "https://img.pokemondb.net/artwork/large/magnemite.jpg", "skills": ["電擊", "放電", "撞擊"]},
    "卡拉卡拉": {"hp": 120, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg", "skills": ["泥巴射擊", "泥巴炸彈", "挖洞"]},
    "喵喵":   {"hp": 124, "atk": 124, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg", "skills": ["抓", "出奇一擊", "撞擊"]},
    "瑪瑙水母": {"hp": 130, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/tentacool.jpg", "skills": ["水槍", "水流尾", "緊束"]},
    "海刺龍": {"hp": 135, "atk": 135, "img": "https://img.pokemondb.net/artwork/large/seadra.jpg", "skills": ["水槍", "水流尾", "逆鱗"]},
    "電擊獸": {"hp": 135, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/electabuzz.jpg", "skills": ["電光", "電擊", "瘋狂伏特"]},
    "鴨嘴火獸": {"hp": 135, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/magmar.jpg", "skills": ["火花", "噴射火焰", "大字爆炎"]},
    "化石翼龍": {"hp": 140, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/aerodactyl.jpg", "skills": ["挖洞", "岩石封鎖", "勇鳥猛攻"]},
    "怪力": {"hp": 140, "atk": 145, "img": "https://img.pokemondb.net/artwork/large/machamp.jpg", "skills": ["雙倍奉還", "岩石封鎖", "近身戰"]},
    "暴鯉龍": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/gyarados.jpg", "skills": ["水槍", "水流尾", "勇鳥猛攻"]},

    # --- 寵物區 ---
    "妙蛙種子": {"hp": 130, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg", "skills": ["藤鞭", "種子炸彈", "污泥炸彈"]},
    "小火龍": {"hp": 112, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg", "skills": ["火花", "噴射火焰", "大字爆炎"]},
    "傑尼龜": {"hp": 121, "atk": 121, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg", "skills": ["水槍", "水流噴射", "水流尾"]},
    "妙蛙花": {"hp": 152, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/venusaur.jpg", "skills": ["藤鞭", "種子炸彈", "污泥炸彈"]},
    "噴火龍": {"hp": 130, "atk": 152, "img": "https://img.pokemondb.net/artwork/large/charizard.jpg", "skills": ["火花", "噴射火焰", "大字爆炎"]},
    "水箭龜": {"hp": 141, "atk": 141, "img": "https://img.pokemondb.net/artwork/large/blastoise.jpg", "skills": ["水槍", "水流噴射", "水流尾"]},
    "毛辮羊": {"hp": 120, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg", "skills": ["撞擊", "撒嬌", "電擊"]},
    "皮卡丘": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg", "skills": ["電光", "放電", "電擊"]},
    "伊布":   {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg", "skills": ["撞擊", "挖洞", "高速星星"]},
    "六尾":   {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/vulpix.jpg", "skills": ["撞擊", "火花", "噴射火焰"]},
    "胖丁":   {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/jigglypuff.jpg", "skills": ["撞擊", "撒嬌", "精神強念"]},
    "皮皮":   {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/clefairy.jpg", "skills": ["撞擊", "撒嬌", "精神強念"]},
    "大蔥鴨": {"hp": 120, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg", "skills": ["啄", "葉刃", "勇鳥猛攻"]},
    "呆呆獸": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg", "skills": ["水槍", "幻象光線", "水流噴射"]},
    "可達鴨": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg", "skills": ["水槍", "幻象光線", "水流噴射"]},
    # 🔥 耿鬼數據更新：HP 96 / ATK 176 🔥
    "耿鬼":   {"hp": 96, "atk": 176, "img": "https://img.pokemondb.net/artwork/large/gengar.jpg", "skills": ["驚嚇", "污泥炸彈", "暗影球"]},
    "卡比獸": {"hp": 175, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/snorlax.jpg", "skills": ["泰山壓頂", "地震", "撞擊"]},
    "吉利蛋": {"hp": 220, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/chansey.jpg", "skills": ["抓", "精神強念", "撞擊"]},
    "幸福蛋": {"hp": 230, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/blissey.jpg", "skills": ["抓", "精神強念", "撞擊"]},
    "拉普拉斯": {"hp": 165, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/lapras.jpg", "skills": ["水槍", "水流噴射", "冰凍光束"]},
    "快龍":   {"hp": 150, "atk": 148, "img": "https://img.pokemondb.net/artwork/large/dragonite.jpg", "skills": ["抓", "逆鱗", "勇鳥猛攻"]},
    
    # [神獸區] (玩家捕獲後的數值)
    "急凍鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/articuno.jpg", "skills": ["冰礫", "冰凍光束", "勇鳥猛攻"]},
    "火焰鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/moltres.jpg", "skills": ["噴射火焰", "大字爆炎", "勇鳥猛攻"]},
    "閃電鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/zapdos.jpg", "skills": ["電光", "瘋狂伏特", "勇鳥猛攻"]},
    "超夢":   {"hp": 152, "atk": 155, "img": "https://img.pokemondb.net/artwork/large/mewtwo.jpg", "skills": ["念力", "精神強念", "精神撃破"]},
    "夢幻":   {"hp": 155, "atk": 152, "img": "https://img.pokemondb.net/artwork/large/mew.jpg", "skills": ["念力", "暗影球", "精神撃破"]},
}

OBTAINABLE_MONS = [
    "妙蛙種子", "小火龍", "傑尼龜", "妙蛙花", "噴火龍", "水箭龜",
    "毛辮羊", "皮卡丘", "伊布", "六尾", "胖丁", "皮皮", "大蔥鴨", "呆呆獸", "可達鴨", "耿鬼",
    "卡比獸", "吉利蛋", "幸福蛋", "拉普拉斯", "快龍",
    "急凍鳥", "火焰鳥", "閃電鳥", "超夢", "夢幻"
]

WILD_UNLOCK_LEVELS = {
    1: ["小拉達"], 2: ["波波"], 3: ["烈雀"], 4: ["阿柏蛇"], 5: ["瓦斯彈"],
    6: ["海星星"], 7: ["角金魚"], 8: ["走路草"], 9: ["穿山鼠"], 10: ["蚊香蝌蚪"],
    12: ["小磁怪"], 14: ["卡拉卡拉"], 16: ["喵喵"], 18: ["瑪瑙水母"], 20: ["海刺龍"],
    22: ["電擊獸"], 24: ["鴨嘴火獸"], 26: ["化石翼龍"], 28: ["怪力"], 30: ["暴鯉龍"]
}

GACHA_NORMAL = [
    {"name": "妙蛙種子", "rate": 5}, {"name": "小火龍", "rate": 5}, {"name": "傑尼龜", "rate": 5}, {"name": "六尾", "rate": 5}, {"name": "毛辮羊", "rate": 5},
    {"name": "伊布", "rate": 10}, {"name": "皮卡丘", "rate": 10}, {"name": "皮皮", "rate": 10}, {"name": "胖丁", "rate": 10}, {"name": "大蔥鴨", "rate": 10},
    {"name": "呆呆獸", "rate": 12.5}, {"name": "可達鴨", "rate": 12.5}
]

GACHA_MEDIUM = [
    {"name": "妙蛙種子", "rate": 10}, {"name": "小火龍", "rate": 10}, {"name": "傑尼龜", "rate": 10},
    {"name": "伊布", "rate": 10}, {"name": "皮卡丘", "rate": 10}, {"name": "呆呆獸", "rate": 10}, {"name": "可達鴨", "rate": 10}, {"name": "毛辮羊", "rate": 10},
    {"name": "卡比獸", "rate": 5},
    {"name": "吉利蛋", "rate": 3}, {"name": "拉普拉斯", "rate": 3}, {"name": "妙蛙花", "rate": 3}, {"name": "噴火龍", "rate": 3}, {"name": "水箭龜", "rate": 3}
]

GACHA_HIGH = [
    {"name": "卡比獸", "rate": 20}, {"name": "吉利蛋", "rate": 20},
    {"name": "幸福蛋", "rate": 10}, {"name": "拉普拉斯", "rate": 10}, {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10},
    {"name": "快龍", "rate": 5}, {"name": "耿鬼", "rate": 5}
]

GACHA_CANDY = [
    {"name": "伊布", "rate": 20}, {"name": "皮卡丘", "rate": 20},
    {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10}, {"name": "卡比獸", "rate": 10}, {"name": "吉利蛋", "rate": 10},
    {"name": "幸福蛋", "rate": 4}, {"name": "拉普拉斯", "rate": 3}, {"name": "快龍", "rate": 3}
]

GACHA_GOLDEN = [
    {"name": "卡比獸", "rate": 30}, {"name": "吉利蛋", "rate": 35}, {"name": "幸福蛋", "rate": 20},
    {"name": "拉普拉斯", "rate": 5}, {"name": "快龍", "rate": 5}, {"name": "耿鬼", "rate": 5}
]

ACTIVE_BATTLES = {}
LEVEL_XP_MAP = {
    1: 50, 2: 150, 3: 300, 4: 500, 5: 800, 6: 1300, 7: 2000, 8: 3000, 9: 5000,
    10: 7000, 11: 9000, 12: 11000, 13: 13000, 14: 15000, 15: 17000, 16: 19000,
    17: 21000, 18: 23000, 19: 25000, 20: 27000, 21: 29000, 22: 31000, 23: 33000, 24: 35000, 25: 37000,
    26: 42000, 27: 47000, 28: 52000, 29: 57000, 30: 62000 
}

RAID_SCHEDULE = [(8, 0), (14, 0), (18, 0), (21, 0), (22, 0), (23, 0)] 
RAID_STATE = {"active": False, "status": "IDLE", "boss": None, "current_hp": 0, "max_hp": 0, "players": {}, "last_attack_time": None, "attack_counter": 0}

# 🔥 Boss 池 (數值高) 🔥
RAID_BOSS_POOL = [
    {"name": "❄️ 急凍鳥", "hp": 15000, "atk": 500, "img": "https://img.pokemondb.net/sprites/home/normal/articuno.png", "weight": 30},
    {"name": "🔥 火焰鳥", "hp": 15000, "atk": 500, "img": "https://img.pokemondb.net/sprites/home/normal/moltres.png", "weight": 30},
    {"name": "⚡ 閃電鳥", "hp": 15000, "atk": 500, "img": "https://img.pokemondb.net/sprites/home/normal/zapdos.png", "weight": 30},
    {"name": "🔮 超夢",   "hp": 20000, "atk": 800, "img": "https://img.pokemondb.net/sprites/home/normal/mewtwo.png", "weight": 5},
    {"name": "✨ 夢幻",   "hp": 20000, "atk": 800, "img": "https://img.pokemondb.net/sprites/home/normal/mew.png", "weight": 5}
]

def get_now_tw():
    return datetime.utcnow() + timedelta(hours=8)

def get_req_xp(lv):
    if lv >= 30: return 999999999
    return LEVEL_XP_MAP.get(lv, 62000)

def apply_iv_stats(base_val, iv, level, is_hp=False, is_player=True):
    iv_mult = 0.9 + (iv / 100) * 0.2
    if is_player:
        growth_rate = 1.08 if is_hp else 1.06
    else:
        growth_rate = 1.09 if is_hp else 1.07
    return int(base_val * iv_mult * (growth_rate ** (level - 1)))

def update_raid_logic(db: Session = None):
    now = get_now_tw()
    curr_total_mins = now.hour * 60 + now.minute
    for (h, m) in RAID_SCHEDULE:
        start_total_mins = h * 60 + m
        lobby_time = start_total_mins - 1
        if lobby_time < 0: lobby_time += 1440 
        if curr_total_mins == lobby_time:
            if RAID_STATE["status"] != "LOBBY":
                # 🔥 隨機抽選 Boss 🔥
                boss_data = random.choices(RAID_BOSS_POOL, weights=[b['weight'] for b in RAID_BOSS_POOL], k=1)[0]
                RAID_STATE["active"] = True
                RAID_STATE["status"] = "LOBBY"
                RAID_STATE["boss"] = boss_data
                RAID_STATE["max_hp"] = boss_data["hp"]
                RAID_STATE["current_hp"] = boss_data["hp"]
                RAID_STATE["players"] = {}
                RAID_STATE["last_attack_time"] = get_now_tw()
                RAID_STATE["attack_counter"] = 0
            return
    
    in_fighting_window = False
    for (h, m) in RAID_SCHEDULE:
        start_total_mins = h * 60 + m
        if 0 <= (curr_total_mins - start_total_mins) < 5:
            in_fighting_window = True
            if RAID_STATE["status"] == "LOBBY":
                 RAID_STATE["status"] = "FIGHTING"
                 RAID_STATE["last_attack_time"] = get_now_tw()
            elif RAID_STATE["status"] == "IDLE":
                 boss_data = random.choices(RAID_BOSS_POOL, weights=[b['weight'] for b in RAID_BOSS_POOL], k=1)[0]
                 RAID_STATE["active"] = True
                 RAID_STATE["status"] = "FIGHTING"
                 RAID_STATE["boss"] = boss_data
                 RAID_STATE["max_hp"] = boss_data["hp"]
                 RAID_STATE["current_hp"] = boss_data["hp"]
                 RAID_STATE["players"] = {}
                 RAID_STATE["last_attack_time"] = get_now_tw()
            
            if RAID_STATE["status"] == "FIGHTING":
                last_time = RAID_STATE.get("last_attack_time")
                if last_time and (get_now_tw() - last_time).total_seconds() >= 7:
                    RAID_STATE["last_attack_time"] = get_now_tw()
                    RAID_STATE["attack_counter"] += 1 
                    
                    base_dmg = int(RAID_STATE["boss"]["atk"] * 0.2)
                    boss_dmg = int(base_dmg * random.uniform(0.95, 1.05)) 
                    
                    # 必須在這裡執行 DB 寫入，確保所有玩家扣血
                    if db:
                        # 找出所有存活玩家
                        active_uids = [uid for uid, p in RAID_STATE["players"].items() if not p.get("dead_at")]
                        if active_uids:
                            users_to_hit = db.query(User).filter(User.id.in_(active_uids)).all()
                            for u in users_to_hit:
                                u.hp = max(0, u.hp - boss_dmg)
                                if u.hp <= 0:
                                    # 標記死亡時間
                                    RAID_STATE["players"][u.id]["dead_at"] = get_now_tw().isoformat()
                            
                            db.commit()

            if RAID_STATE["current_hp"] <= 0:
                RAID_STATE["status"] = "ENDED"
            return
            
    if RAID_STATE["status"] != "IDLE":
        RAID_STATE["active"] = False
        RAID_STATE["status"] = "IDLE"
        RAID_STATE["boss"] = None

@router.get("/data/skills")
def get_skill_data(): return SKILL_DB

@router.get("/pokedex/all")
def get_all_pokedex():
    result = []
    for name, data in POKEDEX_DATA.items():
        is_obtainable = name in OBTAINABLE_MONS
        result.append({ "name": name, "img": data["img"], "hp": data["hp"], "atk": data["atk"], "is_obtainable": is_obtainable })
    return result

@router.get("/wild/list")
def get_wild_list(level: int, current_user: User = Depends(get_current_user)):
    wild_list = []
    for lv in range(1, level + 1):
        species_at_this_lv = WILD_UNLOCK_LEVELS.get(lv)
        if not species_at_this_lv:
            for prev_lv in range(lv - 1, 0, -1):
                if prev_lv in WILD_UNLOCK_LEVELS:
                    species_at_this_lv = WILD_UNLOCK_LEVELS[prev_lv]
                    break
        if not species_at_this_lv:
            species_at_this_lv = ["小拉達"]
        for name in species_at_this_lv:
            if name not in POKEDEX_DATA: continue
            base = POKEDEX_DATA[name]
            wild_hp = int(base["hp"] * 1.3 * (1.09 ** (level - 1)))
            wild_atk = int(base["atk"] * 1.15 * (1.07 ** (level - 1)))
            wild_skills = base.get("skills", ["撞擊", "撞擊", "撞擊"])
            wild_list.append({
                "name": name, "raw_name": name, "is_powerful": False,
                "level": level, "hp": wild_hp, "max_hp": wild_hp, "attack": wild_atk,
                "image_url": base["img"], "skills": wild_skills 
            })
    return wild_list

@router.post("/wild/attack")
async def wild_attack_api(
    is_win: bool = Query(...), 
    is_powerful: bool = Query(False), 
    target_name: str = Query("野怪"), 
    target_level: int = Query(1),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    current_user.hp = current_user.max_hp
    if is_win:
        target_data = POKEDEX_DATA.get(target_name, POKEDEX_DATA["小拉達"])
        base_stat_sum = target_data["hp"] + target_data["atk"]
        xp = int((base_stat_sum / 3) * (1.1 ** (target_level - 1)))
        money = int(xp * 0.6) 
        
        current_user.exp += xp
        current_user.pet_exp += xp
        current_user.money += money
        
        msg = f"獲得 {xp} XP, {money} G"
        inv = json.loads(current_user.inventory)
        if random.random() < 0.4:
            inv["candy"] = inv.get("candy", 0) + 1
            msg += " & 🍬 獲得神奇糖果!"
            
        if is_powerful:
            inv["growth_candy"] = inv.get("growth_candy", 0) + 1
            msg += " & 🍬 成長糖果 x1"
        
        current_user.inventory = json.dumps(inv)
        quests = json.loads(current_user.quests) if current_user.quests else []
        quest_updated = False
        for q in quests:
            is_name_match = (q.get("target") in target_name) or (target_name in q.get("target"))
            # 寬鬆判定
            is_level_match = target_level >= q.get("level", 1)
            if q["status"] != "COMPLETED" and is_name_match and is_level_match:
                q["now"] += 1
                quest_updated = True
        
        if quest_updated: current_user.quests = json.dumps(quests)
        
        req_xp_p = get_req_xp(current_user.level)
        while current_user.exp >= req_xp_p and current_user.level < 30:
            current_user.exp -= req_xp_p; current_user.level += 1; req_xp_p = get_req_xp(current_user.level); msg += f" | 訓練師升級 Lv.{current_user.level}!"
        
        req_xp_pet = get_req_xp(current_user.pet_level)
        pet_leveled_up = False
        while current_user.pet_exp >= req_xp_pet and current_user.pet_level < 30:
            current_user.pet_exp -= req_xp_pet; current_user.pet_level += 1; req_xp_pet = get_req_xp(current_user.pet_level); pet_leveled_up = True; msg += f" | 寶可夢升級 Lv.{current_user.pet_level}!"
        
        box = json.loads(current_user.pokemon_storage)
        active_pet = next((p for p in box if p['uid'] == current_user.active_pokemon_uid), None)
        if active_pet:
            active_pet["exp"] = current_user.pet_exp; active_pet["lv"] = current_user.pet_level
            if pet_leveled_up:
                base = POKEDEX_DATA.get(active_pet["name"])
                if base:
                    current_user.max_hp = apply_iv_stats(base["hp"], active_pet["iv"], current_user.pet_level, is_hp=True, is_player=True)
                    current_user.attack = apply_iv_stats(base["atk"], active_pet["iv"], current_user.pet_level, is_hp=False, is_player=True)
                    current_user.hp = current_user.max_hp
        current_user.pokemon_storage = json.dumps(box)
        db.commit()
        return {"message": f"勝利！HP已回復。{msg}"}
    db.commit()
    return {"message": "戰鬥結束，HP已回復。"}

@router.post("/gacha/{gacha_type}")
async def play_gacha(gacha_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        box = json.loads(current_user.pokemon_storage) if current_user.pokemon_storage else []
    except:
        box = []

    if len(box) >= 25: 
        raise HTTPException(status_code=400, detail="盒子滿了！請先放生")
    
    try:
        inventory = json.loads(current_user.inventory) if current_user.inventory else {}
    except:
        inventory = {}

    cost = 0
    pool = []
    
    if gacha_type == 'normal': pool = GACHA_NORMAL; cost = 1500
    elif gacha_type == 'medium': pool = GACHA_MEDIUM; cost = 3000
    elif gacha_type == 'high': pool = GACHA_HIGH; cost = 10000
    elif gacha_type == 'candy': pool = GACHA_CANDY; cost = 12
    elif gacha_type == 'golden': pool = GACHA_GOLDEN; cost = 3
    else: raise HTTPException(status_code=400, detail="未知類型")
    
    if gacha_type in ['candy', 'golden']:
        key = "candy" if gacha_type == 'candy' else "golden_candy"
        if inventory.get(key, 0) < cost: raise HTTPException(status_code=400, detail="糖果不足")
        inventory[key] -= cost
    else:
        if current_user.money < cost: raise HTTPException(status_code=400, detail="金幣不足")
        current_user.money -= cost
        
    total_rate = sum(p["rate"] for p in pool)
    r = random.uniform(0, total_rate)
    acc = 0
    prize_name = pool[0]["name"]
    for p in pool:
        acc += p["rate"]
        if r <= acc: 
            prize_name = p["name"]
            break
    
    iv = int(random.triangular(0, 100, 50))
    new_mon = { "uid": str(uuid.uuid4()), "name": prize_name, "iv": iv, "lv": 1, "exp": 0 }
    box.append(new_mon)
    
    current_user.pokemon_storage = json.dumps(box)
    current_user.inventory = json.dumps(inventory)
    
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    if prize_name not in unlocked: 
        unlocked.append(prize_name)
        current_user.unlocked_monsters = ",".join(unlocked)
    
    db.commit()
    
    try:
        if gacha_type in ['golden', 'high'] or prize_name in ['快龍', '超夢', '夢幻', '拉普拉斯', '幸福蛋', '耿鬼']:
            await manager.broadcast(f"🎰 恭喜 [{current_user.username}] 獲得了稀有的 [{prize_name}]！")
    except:
        pass
        
    return {"message": f"獲得 {prize_name} (IV: {iv})!", "prize": new_mon, "user": current_user}

@router.post("/box/swap/{pokemon_uid}")
async def swap_active_pokemon(pokemon_uid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage)
    target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到")
    current_user.active_pokemon_uid = pokemon_uid
    current_user.pokemon_name = target["name"]
    
    base = POKEDEX_DATA.get(target["name"])
    current_user.pokemon_image = base["img"] if base else "https://via.placeholder.com/150"
    current_user.pet_level = target["lv"]
    current_user.pet_exp = target["exp"]
    
    if base:
        current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], is_hp=True, is_player=True)
        current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], is_hp=False, is_player=True)
    else:
        current_user.max_hp = 100; current_user.attack = 10
        
    current_user.hp = current_user.max_hp
    db.commit()
    await manager.broadcast(f"EVENT:PVP_SWAP|{current_user.id}")
    return {"message": f"就決定是你了，{target['name']}！"}

@router.post("/box/action/{action}/{pokemon_uid}")
async def box_action(action: str, pokemon_uid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage)
    inv = json.loads(current_user.inventory)
    target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到")
    
    if action == "release":
        if pokemon_uid == current_user.active_pokemon_uid: raise HTTPException(status_code=400, detail="出戰中無法放生")
        box = [p for p in box if p["uid"] != pokemon_uid]
        current_user.money += 100
        msg = "放生成功，獲得 100 Gold"
        
    elif action == "candy":
        if target["lv"] >= current_user.level:
            raise HTTPException(status_code=400, detail=f"等級已達上限 (訓練師 Lv.{current_user.level})")

        if inv.get("growth_candy", 0) < 1: raise HTTPException(status_code=400, detail="成長糖果不足")
        inv["growth_candy"] -= 1
        target["exp"] += 1000
        
        req = get_req_xp(target["lv"])
        while target["exp"] >= req and target["lv"] < 30:
            if target["lv"] >= current_user.level: break
            target["lv"] += 1; target["exp"] -= req; req = get_req_xp(target["lv"])
            
        if pokemon_uid == current_user.active_pokemon_uid:
            base = POKEDEX_DATA.get(target["name"])
            if base:
                current_user.pet_level = target["lv"]; current_user.pet_exp = target["exp"]
                current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], is_hp=True, is_player=True)
                current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], is_hp=False, is_player=True)
                
        msg = f"使用成長糖果，經驗+1000 (Lv.{target['lv']})"
        
    current_user.pokemon_storage = json.dumps(box)
    current_user.inventory = json.dumps(inv)
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

@router.post("/pvp/{target_id}")
async def pvp_attack(target_id: int, damage: int = Query(0), heal: int = Query(0), display_atk: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    battle_key = tuple(sorted((current_user.id, target_id)))
    if battle_key not in ACTIVE_BATTLES: ACTIVE_BATTLES[battle_key] = {"turn": current_user.id}
    if ACTIVE_BATTLES[battle_key]["turn"] != current_user.id: raise HTTPException(status_code=400, detail="還沒輪到你！")
    target = db.query(User).filter(User.id == target_id).first()
    reward_msg = ""
    result_type = "MOVE"
    if heal > 0: current_user.hp = min(current_user.max_hp, current_user.hp + heal)
    if target:
        target.hp = max(0, target.hp - damage)
        if target.hp <= 0:
            result_type = "WIN"
            win_xp = current_user.level * 30
            current_user.exp += win_xp; current_user.pet_exp += win_xp
            reward_msg = f"🏆 勝利！獲得 {win_xp} XP"
            if random.random() < 0.5: current_user.money += 200; reward_msg += " & 💰 200 G"
            else: inv = json.loads(current_user.inventory); inv["candy"] = inv.get("candy", 0) + 1; current_user.inventory = json.dumps(inv); reward_msg += " & 🍬 糖果 x1"
            if battle_key in ACTIVE_BATTLES: del ACTIVE_BATTLES[battle_key]
    db.commit()
    if result_type == "MOVE": ACTIVE_BATTLES[battle_key]["turn"] = target_id
    msg = f"EVENT:PVP_MOVE|{current_user.id}|{target_id}|{damage}|{display_atk}"
    await manager.broadcast(msg)
    return {"message": "攻擊成功", "result": result_type, "reward": reward_msg, "user": current_user}

@router.get("/raid/status")
def get_raid_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_raid_logic(db)
    boss = RAID_STATE.get("boss")
    if not boss: 
        return {"active": False, "status": "IDLE"}
    
    my_status = {}
    if current_user.id in RAID_STATE["players"]:
        p_data = RAID_STATE["players"][current_user.id]
        if p_data.get("dead_at"):
            dead_time = datetime.fromisoformat(p_data["dead_at"])
            if (get_now_tw() - dead_time).total_seconds() > 5:
                del RAID_STATE["players"][current_user.id]
                return {"active": True, "status": "KICKED", "message": "死亡過久已被踢出"}
        my_status = p_data

    return {
        "active": True,
        "status": RAID_STATE["status"],
        "boss_name": boss["name"],
        "boss_atk": boss["atk"], 
        "hp": RAID_STATE["current_hp"],
        "max_hp": RAID_STATE["max_hp"],
        "image": boss["img"],
        "my_status": my_status,
        "attack_counter": RAID_STATE.get("attack_counter", 0)
    }

@router.post("/raid/join")
def join_raid(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_raid_logic(db)
    if RAID_STATE["status"] != "FIGHTING": 
        raise HTTPException(status_code=400, detail="目前戰鬥尚未開始")
    
    if current_user.id in RAID_STATE["players"]: 
        return {"message": "已經加入過了"}
    
    if current_user.money < 1000: 
        raise HTTPException(status_code=400, detail="金幣不足 (需 1000 G)")
    
    current_user.money -= 1000
    RAID_STATE["players"][current_user.id] = {
        "name": current_user.username, 
        "dmg": 0,
        "dead_at": None,
        "claimed": False
    }
    db.commit()
    return {"message": "成功加入團體戰大廳！"}

@router.post("/raid/attack")
def attack_raid_boss(damage: int = Query(...), current_user: User = Depends(get_current_user)):
    update_raid_logic(None)
    
    if current_user.id not in RAID_STATE["players"]:
        raise HTTPException(status_code=400, detail="你不在大廳中")
        
    p_data = RAID_STATE["players"][current_user.id]
    if p_data.get("dead_at"):
        raise HTTPException(status_code=400, detail="你已死亡，請盡快復活！")

    if RAID_STATE["status"] != "FIGHTING": 
        return {"message": "戰鬥尚未開始或已結束", "boss_hp": RAID_STATE["current_hp"]}
    
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
    if current_user.id not in RAID_STATE["players"]:
        raise HTTPException(status_code=400, detail="你不在大廳中")
    
    if current_user.money < 500:
        raise HTTPException(status_code=400, detail="金幣不足 500G")
        
    current_user.money -= 500
    RAID_STATE["players"][current_user.id]["dead_at"] = None
    current_user.hp = current_user.max_hp
    db.commit()
    return {"message": "復活成功！"}

@router.post("/raid/claim")
def claim_raid_reward(choice: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if RAID_STATE["status"] != "ENDED":
        raise HTTPException(status_code=400, detail="戰鬥尚未結束")
    
    if current_user.id not in RAID_STATE["players"]:
        raise HTTPException(status_code=400, detail="你沒有參與這場戰鬥")
        
    p_data = RAID_STATE["players"][current_user.id]
    if p_data.get("claimed"):
        return {"message": "已經領過獎勵了"}
        
    reward_pool = ["gold_candy", "money", "pet"]
    prize = random.choice(reward_pool)
    
    msg = ""
    inv = json.loads(current_user.inventory)
    
    if prize == "gold_candy":
        inv["golden_candy"] = inv.get("golden_candy", 0) + 2
        msg = "獲得 ✨ 黃金糖果 x2"
    elif prize == "money":
        current_user.money += 5000
        msg = "獲得 💰 5000 Gold"
    elif prize == "pet":
        boss_name = RAID_STATE["boss"]["name"].split(" ")[1] 
        new_mon = { 
            "uid": str(uuid.uuid4()), 
            "name": boss_name, 
            "iv": int(random.randint(60, 100)),
            "lv": current_user.pet_level, 
            "exp": 0 
        }
        try:
            box = json.loads(current_user.pokemon_storage)
            box.append(new_mon)
            current_user.pokemon_storage = json.dumps(box)
            msg = f"獲得 Boss 寶可夢：{boss_name}！"
        except:
            msg = "背包滿了，獲得 5000G 代替"
            current_user.money += 5000

    RAID_STATE["players"][current_user.id]["claimed"] = True
    current_user.inventory = json.dumps(inv)
    
    current_user.exp += 3000
    current_user.pet_exp += 3000
    
    db.commit()
    return {"message": msg, "prize": prize}