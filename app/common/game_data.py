# app/common/game_data.py

import random

# =================================================================
# 1. 數值計算公式 (獨立於此)
# =================================================================
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

def get_req_xp(lv): 
    return 999999999 if lv >= 100 else LEVEL_XP_MAP.get(lv, 999999)

def apply_iv_stats(base_val, iv, level, is_hp=False, is_player=True):
    # IV: 0.8 ~ 1.2
    iv_mult = 0.8 + (iv / 100) * 0.4
    if is_player:
        growth_rate = 1.03 if is_hp else 1.031
    else:
        growth_rate = 1.035
    val = int(base_val * iv_mult * (growth_rate ** (level - 1)))
    return max(1, val)

# =================================================================
# 2. 靜態資料庫
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