# app/routers/shop.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
import random
import json
import uuid

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.common.websocket import manager 

router = APIRouter()

# ==========================================
# 1. 完整圖鑑資料庫 (包含所有野怪與神獸)
# ==========================================
POKEDEX_DATA = {
    # [野怪區]
    "小拉達": {"hp": 90, "atk": 80, "img": "https://img.pokemondb.net/artwork/large/rattata.jpg", "skills": ["抓", "出奇一擊", "撞擊"]},
    "波波":   {"hp": 95, "atk": 85, "img": "https://img.pokemondb.net/artwork/large/pidgey.jpg", "skills": ["抓", "啄", "燕返"]},
    "烈雀":   {"hp": 90, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/spearow.jpg", "skills": ["抓", "啄", "燕返"]},
    "阿柏蛇": {"hp": 100, "atk": 95, "img": "https://img.pokemondb.net/artwork/large/ekans.jpg", "skills": ["毒針", "毒擊", "緊束"]},
    "瓦斯彈": {"hp": 110, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/koffing.jpg", "skills": ["毒針", "毒針", "撞擊"]},
    "海星星": {"hp": 100, "atk": 100, "img": "https://img.pokemondb.net/artwork/large/staryu.jpg", "skills": ["水槍", "幻象光線", "撞擊"]},
    "角金魚": {"hp": 110, "atk": 95, "img": "https://img.pokemondb.net/artwork/large/goldeen.jpg", "skills": ["水槍", "幻象光線", "泥巴射擊"]},
    "走路草": {"hp": 100, "atk": 85, "img": "https://img.pokemondb.net/artwork/large/oddish.jpg", "skills": ["種子炸彈", "撞擊", "毒擊"]},
    "穿山鼠": {"hp": 120, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/sandshrew.jpg", "skills": ["抓", "泥巴射擊", "泥巴炸彈"]},
    "蚊香蝌蚪": {"hp": 122, "atk": 108, "img": "https://img.pokemondb.net/artwork/large/poliwag.jpg", "skills": ["雙倍奉還", "冰凍光束", "水槍"]},
    "小磁怪": {"hp": 120, "atk": 114, "img": "https://img.pokemondb.net/artwork/large/magnemite.jpg", "skills": ["電擊", "放電", "撞擊"]},
    "卡拉卡拉": {"hp": 120, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg", "skills": ["泥巴射擊", "泥巴炸彈", "挖洞"]},
    "喵喵":   {"hp": 124, "atk": 124, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg", "skills": ["抓", "出奇一擊", "撞擊"]},
    "瑪瑙水母": {"hp": 130, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/tentacool.jpg", "skills": ["水槍", "水流尾", "緊束"]},
    "海刺龍": {"hp": 135, "atk": 135, "img": "https://img.pokemondb.net/artwork/large/seadra.jpg", "skills": ["水槍", "水流尾", "逆鱗"]},
    "蚊香勇士": {"hp": 160, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/poliwrath.jpg", "skills": ["雙倍奉還", "冰凍光束", "水槍"]},
    "暴鯉龍": {"hp": 180, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/gyarados.jpg", "skills": ["水流尾", "咬碎", "破壞光線"]},

    # [寵物區]
    "妙蛙種子": {"hp": 130, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg", "skills": ["藤鞭", "種子炸彈", "污泥炸彈"]},
    "小火龍": {"hp": 112, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg", "skills": ["火花", "噴射火焰", "大字爆炎"]},
    "傑尼龜": {"hp": 121, "atk": 121, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg", "skills": ["水槍", "水流噴射", "水流尾"]},
    "妙蛙花": {"hp": 152, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/venusaur.jpg", "skills": ["藤鞭", "種子炸彈", "污泥炸彈"]},
    "噴火龍": {"hp": 130, "atk": 152, "img": "https://img.pokemondb.net/artwork/large/charizard.jpg", "skills": ["火花", "噴射火焰", "大字爆炎"]},
    "水箭龜": {"hp": 141, "atk": 141, "img": "https://img.pokemondb.net/artwork/large/blastoise.jpg", "skills": ["水槍", "水流噴射", "水流尾"]},
    "毛辮羊": {"hp": 120, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg", "skills": ["撞擊", "撒嬌", "電擊"]},
    "皮卡丘": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg", "skills": ["電光", "放電", "電擊"]},
    "伊布":   {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg", "skills": ["撞擊", "挖洞", "高速星星"]},
    "胖丁":   {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/jigglypuff.jpg", "skills": ["撞擊", "撒嬌", "精神強念"]},
    "皮皮":   {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/clefairy.jpg", "skills": ["撞擊", "撒嬌", "精神強念"]},
    "大蔥鴨": {"hp": 120, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg", "skills": ["啄", "葉刃", "勇鳥猛攻"]},
    "呆呆獸": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg", "skills": ["水槍", "幻象光線", "水流噴射"]},
    "可達鴨": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg", "skills": ["水槍", "幻象光線", "水流噴射"]},
    "卡比獸": {"hp": 175, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/snorlax.jpg", "skills": ["泰山壓頂", "地震", "撞擊"]},
    "吉利蛋": {"hp": 220, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/chansey.jpg", "skills": ["抓", "精神強念", "撞擊"]},
    "幸福蛋": {"hp": 230, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/blissey.jpg", "skills": ["抓", "精神強念", "撞擊"]},
    "拉普拉斯": {"hp": 165, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/lapras.jpg", "skills": ["水槍", "水流噴射", "冰凍光束"]},
    "快龍":   {"hp": 150, "atk": 148, "img": "https://img.pokemondb.net/artwork/large/dragonite.jpg", "skills": ["抓", "逆鱗", "勇鳥猛攻"]},
    
    # [神獸區]
    "急凍鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/articuno.jpg", "skills": ["冰礫", "冰凍光束", "勇鳥猛攻"]},
    "火焰鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/moltres.jpg", "skills": ["噴射火焰", "大字爆炎", "勇鳥猛攻"]},
    "閃電鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/zapdos.jpg", "skills": ["電光", "瘋狂伏特", "勇鳥猛攻"]},
    "超夢":   {"hp": 152, "atk": 155, "img": "https://img.pokemondb.net/artwork/large/mewtwo.jpg", "skills": ["念力", "精神強念", "精神撃破"]},
    "夢幻":   {"hp": 155, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/mew.jpg", "skills": ["念力", "精神強念", "精神撃破"]},
}

# --------------------------------------------------------
# 2. 清單與常數
# --------------------------------------------------------
OBTAINABLE_MONS = [
    "妙蛙種子", "小火龍", "傑尼龜", "妙蛙花", "噴火龍", "水箭龜",
    "毛辮羊", "皮卡丘", "伊布", "胖丁", "皮皮", "大蔥鴨", "呆呆獸", "可達鴨",
    "卡比獸", "吉利蛋", "幸福蛋", "拉普拉斯", "快龍",
    "急凍鳥", "火焰鳥", "閃電鳥", "超夢", "夢幻"
]

WILD_UNLOCK_LEVELS = {
    1: ["小拉達"], 2: ["波波"], 3: ["烈雀"], 4: ["阿柏蛇"], 5: ["瓦斯彈"],
    6: ["海星星"], 7: ["角金魚"], 8: ["走路草"], 9: ["穿山鼠"], 10: ["蚊香蝌蚪"],
    12: ["小磁怪"], 14: ["卡拉卡拉"], 16: ["喵喵"], 18: ["瑪瑙水母"], 20: ["海刺龍"]
}

GACHA_HIGH = [{"name": "卡比獸", "rate": 20}, {"name": "吉利蛋", "rate": 24}, {"name": "幸福蛋", "rate": 10}, {"name": "拉普拉斯", "rate": 10}, {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10}, {"name": "快龍", "rate": 6}]
GACHA_GOLDEN = [{"name": "卡比獸", "rate": 30}, {"name": "吉利蛋", "rate": 35}, {"name": "幸福蛋", "rate": 20}, {"name": "拉普拉斯", "rate": 10}, {"name": "快龍", "rate": 5}]
GACHA_NORMAL = [{"name": "妙蛙種子", "rate": 5}, {"name": "小火龍", "rate": 5}, {"name": "傑尼龜", "rate": 5}, {"name": "伊布", "rate": 8}, {"name": "皮卡丘", "rate": 8}, {"name": "皮皮", "rate": 10}, {"name": "胖丁", "rate": 10}, {"name": "毛辮羊", "rate": 8}, {"name": "大蔥鴨", "rate": 12}, {"name": "呆呆獸", "rate": 12}, {"name": "可達鴨", "rate": 12}, {"name": "卡比獸", "rate": 2}, {"name": "吉利蛋", "rate": 2}]
GACHA_MEDIUM = [{"name": "妙蛙種子", "rate": 10}, {"name": "小火龍", "rate": 10}, {"name": "傑尼龜", "rate": 10}, {"name": "伊布", "rate": 10}, {"name": "皮卡丘", "rate": 10}, {"name": "呆呆獸", "rate": 10}, {"name": "可達鴨", "rate": 10}, {"name": "毛辮羊", "rate": 10}, {"name": "卡比獸", "rate": 5}, {"name": "吉利蛋", "rate": 3}, {"name": "拉普拉斯", "rate": 3}, {"name": "妙蛙花", "rate": 3}, {"name": "噴火龍", "rate": 3}, {"name": "水箭龜", "rate": 3}]
GACHA_CANDY = [{"name": "伊布", "rate": 20}, {"name": "皮卡丘", "rate": 20}, {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10}, {"name": "卡比獸", "rate": 10}, {"name": "吉利蛋", "rate": 10}, {"name": "幸福蛋", "rate": 4}, {"name": "拉普拉斯", "rate": 3}, {"name": "快龍", "rate": 3}]

ACTIVE_BATTLES = {}
LEVEL_XP = { 1: 50, 2: 150, 3: 300, 4: 500, 5: 800, 6: 1300, 7: 2000, 8: 3000, 9: 5000 }

RAID_SCHEDULE = [8, 18, 22] 
RAID_STATE = {"active": False, "status": "IDLE", "boss": None, "current_hp": 0, "max_hp": 0, "players": {}}
LEGENDARY_BIRDS = [
    {"name": "❄️ 急凍鳥", "hp": 50000, "atk": 300, "img": "https://img.pokemondb.net/sprites/home/normal/articuno.png"},
    {"name": "⚡ 閃電鳥", "hp": 50000, "atk": 320, "img": "https://img.pokemondb.net/sprites/home/normal/zapdos.png"},
    {"name": "🔥 火焰鳥", "hp": 50000, "atk": 350, "img": "https://img.pokemondb.net/sprites/home/normal/moltres.png"}
]

SKILL_DB = {
    "水槍": {"dmg": 14, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "撒嬌": {"dmg": 14, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "念力": {"dmg": 14, "effect": "heal", "prob": 0.5, "val": 0.15, "desc": "50%回血15%"},
    "毒針": {"dmg": 14, "effect": "buff_atk", "prob": 0.5, "val": 0.2, "desc": "50%加攻20%"},
    "藤鞭": {"dmg": 16, "effect": "buff_atk", "prob": 0.35, "val": 0.2, "desc": "35%加攻20%"},
    "火花": {"dmg": 16, "effect": "buff_atk", "prob": 0.35, "val": 0.2, "desc": "35%加攻20%"},
    "電光": {"dmg": 16, "effect": "buff_atk", "prob": 0.35, "val": 0.2, "desc": "35%加攻20%"},
    "挖洞": {"dmg": 16, "effect": "buff_atk", "prob": 0.35, "val": 0.2, "desc": "35%加攻20%"},
    "地震": {"dmg": 16, "effect": "heal", "prob": 0.35, "val": 0.2, "desc": "35%回血20%"},
    "冰礫": {"dmg": 16, "effect": "heal", "prob": 0.35, "val": 0.2, "desc": "35%回血20%"},
    "泥巴射擊": {"dmg": 18, "effect": "buff_atk", "prob": 0.3, "val": 0.2, "desc": "30%加攻20%"},
    "污泥炸彈": {"dmg": 18, "effect": "buff_atk", "prob": 0.3, "val": 0.2, "desc": "30%加攻20%"},
    "噴射火焰": {"dmg": 18, "effect": "buff_atk", "prob": 0.3, "val": 0.2, "desc": "30%加攻20%"},
    "水流噴射": {"dmg": 18, "effect": "buff_atk", "prob": 0.3, "val": 0.2, "desc": "30%加攻20%"},
    "精神強念": {"dmg": 18, "effect": "buff_atk", "prob": 0.3, "val": 0.2, "desc": "30%加攻20%"},
    "電擊":     {"dmg": 18, "effect": "buff_atk", "prob": 0.3, "val": 0.2, "desc": "30%加攻20%"},
    "撞擊": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "啄":   {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "緊束": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "葉刃": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "咬碎": {"dmg": 24, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
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
    "雙倍奉還": {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "逆鱗":     {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "精神撃破": {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "破壞光線": {"dmg": 28, "effect": None, "prob": 0, "val": 0, "desc": "無特效"},
    "勇鳥猛攻": {"dmg": 34, "effect": "recoil", "prob": 1.0, "val": 0.1, "desc": "扣自身10%血"}
}

# ==========================================
# 3. 輔助函式
# ==========================================
def get_req_xp(lv):
    if lv >= 25: return 999999999
    if lv < 10: return LEVEL_XP.get(lv, 5000)
    return 5000 + (lv - 9) * 2000

def apply_iv_stats(base_val, iv, level, is_player=True):
    iv_mult = 0.9 + (iv / 100) * 0.2
    growth = 1.06 if is_player else 1.07
    if base_val > 500: growth = 1.08 if is_player else 1.09
    return int(base_val * iv_mult * (growth ** (level - 1)))

def update_raid_logic():
    now = datetime.now()
    current_hour = now.hour
    current_min = now.minute
    
    next_hour = current_hour + 1
    if current_min == 59 and next_hour in RAID_SCHEDULE:
        if RAID_STATE["status"] != "LOBBY":
            boss_template = random.choice(LEGENDARY_BIRDS)
            RAID_STATE["active"] = True
            RAID_STATE["status"] = "LOBBY"
            RAID_STATE["boss"] = boss_template
            RAID_STATE["max_hp"] = boss_template["hp"]
            RAID_STATE["current_hp"] = boss_template["hp"]
            RAID_STATE["players"] = {}
        return

    if current_hour in RAID_SCHEDULE and 0 <= current_min < 30:
        if RAID_STATE["status"] == "LOBBY":
             RAID_STATE["status"] = "FIGHTING"
        elif RAID_STATE["status"] == "IDLE":
             boss_template = random.choice(LEGENDARY_BIRDS)
             RAID_STATE["active"] = True
             RAID_STATE["status"] = "FIGHTING"
             RAID_STATE["boss"] = boss_template
             RAID_STATE["max_hp"] = boss_template["hp"]
             RAID_STATE["current_hp"] = boss_template["hp"]
             RAID_STATE["players"] = {}
        
        if RAID_STATE["current_hp"] <= 0:
            RAID_STATE["status"] = "ENDED"
            RAID_STATE["active"] = False
        return

    if RAID_STATE["status"] != "IDLE":
        RAID_STATE["active"] = False
        RAID_STATE["status"] = "IDLE"
        RAID_STATE["boss"] = None

# ==========================================
# 4. API Endpoints
# ==========================================

@router.get("/data/skills")
def get_skill_data():
    return SKILL_DB

@router.get("/pokedex/all")
def get_all_pokedex():
    result = []
    # 🔥 關鍵：回傳所有資料給盒子使用，但標記 is_obtainable 讓圖鑑過濾
    for name, data in POKEDEX_DATA.items():
        is_obtainable = name in OBTAINABLE_MONS
        result.append({
            "name": name, 
            "img": data["img"], 
            "hp": data["hp"], 
            "atk": data["atk"],
            "is_obtainable": is_obtainable # 🔥 前端用這個來過濾黑影
        })
    return result

@router.get("/wild/list")
def get_wild_list(level: int, current_user: User = Depends(get_current_user)):
    wild_list = []
    available_species = []
    for unlock_lv, species_list in WILD_UNLOCK_LEVELS.items():
        if unlock_lv <= level:
            available_species.extend(species_list)
    if not available_species: available_species = ["小拉達"]
    
    for name in available_species:
        if name not in POKEDEX_DATA: continue
        base = POKEDEX_DATA[name]
        
        mult = 1.0
        wild_hp = int(base["hp"] * 1.3 * mult * (1.09 ** (level - 1)))
        wild_atk = int(base["atk"] * 1.15 * mult * (1.07 ** (level - 1)))
        wild_skills = base.get("skills", ["撞擊", "撞擊", "撞擊"])
        
        wild_list.append({
            "name": name, "raw_name": name, "is_powerful": False,
            "level": level, "hp": wild_hp, "max_hp": wild_hp, "attack": wild_atk,
            "image_url": base["img"], "skills": wild_skills 
        })
    return wild_list

@router.post("/wild/attack")
async def wild_attack_api(is_win: bool = Query(...), is_powerful: bool = Query(False), target_name: str = Query("野怪"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.hp = current_user.max_hp
    if is_win:
        xp = current_user.level * 50; money = current_user.level * 30
        current_user.exp += xp; current_user.pet_exp += xp; current_user.money += money
        msg = f"獲得 {xp} XP, {money} G"
        if is_powerful:
            inv = json.loads(current_user.inventory); inv["growth_candy"] = inv.get("growth_candy", 0) + 1; current_user.inventory = json.dumps(inv); msg += " & 🍬 成長糖果 x1"
        
        quests = json.loads(current_user.quests) if current_user.quests else []
        quest_updated = False
        
        for q in quests:
            is_match = (q.get("target") in target_name) or (target_name in q.get("target"))
            if q["status"] != "COMPLETED" and is_match:
                q["now"] += 1
                quest_updated = True
        
        if quest_updated: current_user.quests = json.dumps(quests)
        
        req_xp_p = get_req_xp(current_user.level)
        while current_user.exp >= req_xp_p and current_user.level < 25:
            current_user.exp -= req_xp_p; current_user.level += 1; req_xp_p = get_req_xp(current_user.level); msg += f" | 訓練師升級 Lv.{current_user.level}!"
        
        req_xp_pet = get_req_xp(current_user.pet_level)
        pet_leveled_up = False
        while current_user.pet_exp >= req_xp_pet and current_user.pet_level < 25:
            current_user.pet_exp -= req_xp_pet; current_user.pet_level += 1; req_xp_pet = get_req_xp(current_user.pet_level); pet_leveled_up = True; msg += f" | 寶可夢升級 Lv.{current_user.pet_level}!"
        
        box = json.loads(current_user.pokemon_storage)
        active_pet = next((p for p in box if p['uid'] == current_user.active_pokemon_uid), None)
        if active_pet:
            active_pet["exp"] = current_user.pet_exp; active_pet["lv"] = current_user.pet_level
            if pet_leveled_up:
                base = POKEDEX_DATA.get(active_pet["name"])
                if base:
                    current_user.max_hp = apply_iv_stats(base["hp"], active_pet["iv"], current_user.pet_level)
                    current_user.attack = apply_iv_stats(base["atk"], active_pet["iv"], current_user.pet_level)
                    current_user.hp = current_user.max_hp
        current_user.pokemon_storage = json.dumps(box)
        db.commit()
        return {"message": f"勝利！HP已回復。{msg}"}
    db.commit()
    return {"message": "戰鬥結束，HP已回復。"}

@router.post("/gacha/{gacha_type}")
async def play_gacha(gacha_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage)
    if len(box) >= 25: raise HTTPException(status_code=400, detail="盒子滿了！請先放生")
    inventory = json.loads(current_user.inventory)
    cost, pool = 0, []
    
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
    r = random.randint(1, total_rate)
    acc = 0; prize_name = pool[0]["name"]
    for p in pool:
        acc += p["rate"]
        if r <= acc: prize_name = p["name"]; break
    
    iv = int(random.triangular(0, 100, 50))
    new_mon = { "uid": str(uuid.uuid4()), "name": prize_name, "iv": iv, "lv": 1, "exp": 0 }
    box.append(new_mon)
    
    current_user.pokemon_storage = json.dumps(box)
    current_user.inventory = json.dumps(inventory)
    
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    if prize_name not in unlocked: unlocked.append(prize_name); current_user.unlocked_monsters = ",".join(unlocked)
    
    db.commit()
    
    if gacha_type in ['golden', 'high'] or prize_name in ['快龍', '超夢', '夢幻', '拉普拉斯', '幸福蛋']:
        await manager.broadcast(f"🎰 恭喜 [{current_user.username}] 獲得了稀有的 [{prize_name}]！")
        
    return {"message": f"獲得 {prize_name} (IV: {iv})!", "prize": new_mon, "user": current_user}

@router.post("/box/swap/{pokemon_uid}")
async def swap_active_pokemon(pokemon_uid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage)
    target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到")
    
    current_user.active_pokemon_uid = pokemon_uid
    current_user.pokemon_name = target["name"]
    
    def apply_iv_stats_local(base_val, iv, level):
        iv_mult = 0.9 + (iv / 100) * 0.2
        return int(base_val * iv_mult * (1.06 ** (level - 1)))
        
    base = POKEDEX_DATA.get(target["name"])
    current_user.pokemon_image = base["img"] if base else "https://via.placeholder.com/150"
    
    current_user.pet_level = target["lv"]
    current_user.pet_exp = target["exp"]
    
    if base:
        current_user.max_hp = apply_iv_stats_local(base["hp"], target["iv"], target["lv"])
        current_user.attack = apply_iv_stats_local(base["atk"], target["iv"], target["lv"])
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
        while target["exp"] >= req and target["lv"] < 25:
            if target["lv"] >= current_user.level: break
            target["lv"] += 1; target["exp"] -= req; req = get_req_xp(target["lv"])
            
        if pokemon_uid == current_user.active_pokemon_uid:
            base = POKEDEX_DATA.get(target["name"])
            def apply_iv_stats_local(base_val, iv, level):
                iv_mult = 0.9 + (iv / 100) * 0.2
                return int(base_val * iv_mult * (1.06 ** (level - 1)))
            
            if base:
                current_user.pet_level = target["lv"]; current_user.pet_exp = target["exp"]
                current_user.max_hp = apply_iv_stats_local(base["hp"], target["iv"], target["lv"])
                current_user.attack = apply_iv_stats_local(base["atk"], target["iv"], target["lv"])
                
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

# 🔥 修正 500 Error: 確保 boss 存在才讀取 🔥
@router.get("/raid/status")
def get_raid_status():
    update_raid_logic()
    if not RAID_STATE["active"] and RAID_STATE["status"] != "LOBBY":
        return {"active": False, "status": "IDLE"}
    
    boss = RAID_STATE.get("boss")
    # 如果 boss 為 None (剛啟動時)，直接回傳 IDLE
    if not boss:
        return {"active": False, "status": "IDLE"}
        
    return {
        "active": True,
        "status": RAID_STATE["status"],
        "boss_name": boss["name"],
        "hp": RAID_STATE["current_hp"],
        "max_hp": RAID_STATE["max_hp"],
        "image": boss["img"]
    }

@router.post("/raid/join")
def join_raid(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_raid_logic()
    if RAID_STATE["status"] not in ["LOBBY", "FIGHTING"]: raise HTTPException(status_code=400, detail="目前沒有開放團體戰")
    if current_user.id in RAID_STATE["players"]: return {"message": "已經加入過了"}
    if current_user.money < 1000: raise HTTPException(status_code=400, detail="金幣不足 (需 1000 G)")
    current_user.money -= 1000
    RAID_STATE["players"][current_user.id] = {"name": current_user.username, "dmg": 0}
    db.commit()
    return {"message": "成功加入團體戰大廳！"}

@router.post("/raid/attack")
def attack_raid_boss(damage: int = Query(...), current_user: User = Depends(get_current_user)):
    if RAID_STATE["status"] != "FIGHTING": return {"message": "戰鬥尚未開始或已結束", "boss_hp": RAID_STATE["current_hp"]}
    RAID_STATE["current_hp"] = max(0, RAID_STATE["current_hp"] - damage)
    return {"message": f"造成 {damage} 點傷害", "boss_hp": RAID_STATE["current_hp"]}