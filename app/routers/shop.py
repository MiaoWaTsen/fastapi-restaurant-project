# app/routers/shop.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, time
import random
import json
import uuid

from app.db.session import get_db
from app.common.deps import get_current_user
from app.models.user import User
from app.common.websocket import manager 

router = APIRouter()

# 完整圖鑑 (含技能組)
POKEDEX_DATA = {
    # 野怪/玩家通用
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

    # 玩家/扭蛋限定
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
    "急凍鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/articuno.jpg", "skills": ["冰礫", "冰凍光束", "勇鳥猛攻"]},
    "火焰鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/moltres.jpg", "skills": ["噴射火焰", "大字爆炎", "勇鳥猛攻"]},
    "閃電鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/zapdos.jpg", "skills": ["電光", "瘋狂伏特", "勇鳥猛攻"]},
    "超夢":   {"hp": 152, "atk": 155, "img": "https://img.pokemondb.net/artwork/large/mewtwo.jpg", "skills": ["念力", "精神強念", "精神撃破"]},
    "夢幻":   {"hp": 155, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/mew.jpg", "skills": ["念力", "精神強念", "精神撃破"]},
}

# 技能數據庫
SKILL_DATA = {
    "水槍": 14, "撒嬌": 14, "念力": 14, "毒針": 14,
    "藤鞭": 16, "火花": 16, "電光": 16, "挖洞": 16, "地震": 16, "冰礫": 16,
    "泥巴射擊": 18, "污泥炸彈": 18, "噴射火焰": 18, "水流噴射": 18, "精神強念": 18, "電擊": 18,
    "撞擊": 24, "啄": 24, "緊束": 24, "葉刃": 24,
    "抓": 26, "放電": 26, "出奇一擊": 26, "毒擊": 26, "幻象光線": 26, "水流尾": 26, "燕返": 26, "種子炸彈": 26,
    "高速星星": 26, "泰山壓頂": 26, "大字爆炎": 26, "泥巴炸彈": 26, "冰凍光束": 26, "瘋狂伏特": 26,
    "雙倍奉還": 28, "逆鱗": 28, "精神撃破": 28,
    "勇鳥猛攻": 34, "破壞光線": 34, "咬碎": 24
}

# 野怪解鎖順序 (等級 -> 寶可夢)
WILD_UNLOCKS = {
    1: ["小拉達"], 2: ["波波"], 3: ["烈雀"], 4: ["阿柏蛇"], 5: ["瓦斯彈"],
    6: ["海星星"], 7: ["角金魚"], 8: ["走路草"], 9: ["穿山鼠"], 10: ["蚊香蝌蚪"],
    12: ["小磁怪"], 14: ["卡拉卡拉"], 16: ["喵喵"], 18: ["瑪瑙水母"], 20: ["海刺龍"]
}

# 扭蛋池
GACHA_HIGH = [{"name": "卡比獸", "rate": 20}, {"name": "吉利蛋", "rate": 24}, {"name": "幸福蛋", "rate": 10}, {"name": "拉普拉斯", "rate": 10}, {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10}, {"name": "快龍", "rate": 6}]
GACHA_GOLDEN = [{"name": "卡比獸", "rate": 30}, {"name": "吉利蛋", "rate": 35}, {"name": "幸福蛋", "rate": 20}, {"name": "拉普拉斯", "rate": 10}, {"name": "快龍", "rate": 5}]
GACHA_NORMAL = [{"name": "妙蛙種子", "rate": 5}, {"name": "小火龍", "rate": 5}, {"name": "傑尼龜", "rate": 5}, {"name": "伊布", "rate": 8}, {"name": "皮卡丘", "rate": 8}, {"name": "皮皮", "rate": 10}, {"name": "胖丁", "rate": 10}, {"name": "毛辮羊", "rate": 8}, {"name": "大蔥鴨", "rate": 12}, {"name": "呆呆獸", "rate": 12}, {"name": "可達鴨", "rate": 12}, {"name": "卡比獸", "rate": 2}, {"name": "吉利蛋", "rate": 2}]
GACHA_MEDIUM = [{"name": "妙蛙種子", "rate": 10}, {"name": "小火龍", "rate": 10}, {"name": "傑尼龜", "rate": 10}, {"name": "伊布", "rate": 10}, {"name": "皮卡丘", "rate": 10}, {"name": "呆呆獸", "rate": 10}, {"name": "可達鴨", "rate": 10}, {"name": "毛辮羊", "rate": 10}, {"name": "卡比獸", "rate": 5}, {"name": "吉利蛋", "rate": 3}, {"name": "拉普拉斯", "rate": 3}, {"name": "妙蛙花", "rate": 3}, {"name": "噴火龍", "rate": 3}, {"name": "水箭龜", "rate": 3}]
GACHA_CANDY = [{"name": "伊布", "rate": 20}, {"name": "皮卡丘", "rate": 20}, {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10}, {"name": "卡比獸", "rate": 10}, {"name": "吉利蛋", "rate": 10}, {"name": "幸福蛋", "rate": 4}, {"name": "拉普拉斯", "rate": 3}, {"name": "快龍", "rate": 3}]

ACTIVE_BATTLES = {}
RAID_STATE = {"boss_name": None, "hp": 0, "max_hp": 0, "active": False, "players": {}}
LEVEL_XP = { 1: 50, 2: 150, 3: 300, 4: 500, 5: 800, 6: 1300, 7: 2000, 8: 3000, 9: 5000 }

def get_req_xp(lv):
    if lv >= 25: return 999999999
    if lv < 10: return LEVEL_XP.get(lv, 5000)
    return 5000 + (lv - 9) * 2000

def apply_iv_stats(base_val, iv, level, is_player=True):
    iv_mult = 0.9 + (iv / 100) * 0.2
    growth = 1.06 if is_player else 1.07
    if base_val > 500: growth = 1.08 if is_player else 1.09
    return int(base_val * iv_mult * (growth ** (level - 1)))

@router.get("/data/skills")
def get_skill_data():
    return SKILL_DATA

# 🔥 1. 野怪列表 API (V3.1) 🔥
@router.get("/wild/list")
def get_wild_list(level: int, current_user: User = Depends(get_current_user)):
    wild_list = []
    
    # 根據玩家等級建立野怪池
    available_species = []
    for unlock_lv, species_list in WILD_UNLOCKS.items():
        if unlock_lv <= level:
            available_species.extend(species_list)
            
    if not available_species: available_species = ["小拉達"]
    
    for _ in range(6):
        try:
            name = random.choice(available_species)
            if name not in POKEDEX_DATA: name = "小拉達"
            base = POKEDEX_DATA[name]
            
            is_powerful = random.random() < 0.05
            mult = 1.2 if is_powerful else 1.0
            
            wild_hp = int(base["hp"] * 1.3 * mult * (1.09 ** (level - 1)))
            wild_atk = int(base["atk"] * 1.15 * mult * (1.07 ** (level - 1)))
            wild_skills = base.get("skills", ["撞擊", "撞擊", "撞擊"])
            
            wild_list.append({
                "name": f"💪 {name}" if is_powerful else name,
                "raw_name": name,
                "is_powerful": is_powerful,
                "level": level,
                "hp": wild_hp, "max_hp": wild_hp, "attack": wild_atk,
                "image_url": base["img"],
                "skills": wild_skills 
            })
        except: continue
        
    return wild_list

# 🔥 2. 任務系統 (V3.1 補齊3個任務) 🔥
def generate_quests(user_level, count=3):
    new_quests = []
    # 建立目前可解鎖的怪獸池
    targets_pool = []
    for u_lv, species in WILD_UNLOCKS.items():
        if u_lv <= user_level: targets_pool.extend(species)
    if not targets_pool: targets_pool = ["小拉達"]
    
    for _ in range(count):
        target = random.choice(targets_pool)
        req_count = random.randint(1, 3) + int(user_level/3)
        is_golden = random.random() < 0.15
        
        q = {
            "id": str(uuid.uuid4()),
            "type": "GOLDEN" if is_golden else "NORMAL",
            "target": target, # 存原始名稱
            "target_display": f"Lv.{user_level} {target}", # 顯示名稱
            "target_lv": user_level,
            "req": req_count,
            "now": 0,
            "gold": req_count * 150,
            "xp": req_count * 80,
            "status": "WAITING"
        }
        if is_golden: q["gold"] = 0; q["xp"] = 0
        new_quests.append(q)
        
    return new_quests

@router.get("/quests/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quests = json.loads(current_user.quests) if current_user.quests else []
    
    # 檢查有效任務數量
    active_or_waiting = [q for q in quests if q["status"] in ["ACTIVE", "WAITING"]]
    needed = 3 - len(active_or_waiting)
    
    if needed > 0:
        new_qs = generate_quests(current_user.level, count=needed)
        # 把新的加進去
        quests.extend(new_qs)
        # 為了保持整潔，可以移除已完成很久的，這裡先簡單覆蓋
        # 只保留 Active/Waiting 和 新的，加上最近完成的
        final_list = active_or_waiting + new_qs
        # 如果有剛領取的 Completed 狀態，前端會呼叫 claim 移除，所以這裡只需補齊
        # 但要注意 quests 變數現在只包含 active/waiting，所以要小心不要把 client 還沒 claim 的 completed 弄丟
        # 正確做法：保留所有，然後補齊
        # 重新讀取
        all_quests = json.loads(current_user.quests) if current_user.quests else []
        # 移除已經 Claimed (通常 claim API 會移除)
        # 這裡我們只負責「如果 Active+Waiting 不足 3，就新增」
        real_active = [q for q in all_quests if q["status"] in ["ACTIVE", "WAITING"]]
        if len(real_active) < 3:
            all_quests.extend(new_qs)
            current_user.quests = json.dumps(all_quests)
            db.commit()
            return all_quests
    
    return quests

@router.post("/quests/accept/{qid}")
def accept_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quests = json.loads(current_user.quests)
    for q in quests:
        if q["id"] == qid and q["status"] == "WAITING":
            q["status"] = "ACTIVE"
            current_user.quests = json.dumps(quests); db.commit()
            return {"message": "任務已接受"}
    raise HTTPException(status_code=400, detail="無法接受此任務")

@router.post("/quests/abandon/{qid}")
def abandon_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 1000: raise HTTPException(status_code=400, detail="刪除任務需 1000 Gold")
    quests = json.loads(current_user.quests)
    # 移除該任務
    new_quests = [q for q in quests if q["id"] != qid]
    if len(new_quests) == len(quests): raise HTTPException(status_code=404, detail="找不到任務")
    
    current_user.money -= 1000
    # 補 1 個新任務
    new_q = generate_quests(current_user.level, count=1)[0]
    new_quests.append(new_q)
    
    current_user.quests = json.dumps(new_quests); db.commit()
    return {"message": "任務已刪除並刷新 (-1000G)"}

@router.post("/quests/claim/{qid}")
def claim_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quests = json.loads(current_user.quests)
    inv = json.loads(current_user.inventory)
    target_q = None
    for q in quests:
        if q["id"] == qid and q["status"] == "COMPLETED": target_q = q; break
    if not target_q: raise HTTPException(status_code=400, detail="無法領取")
    
    msg = ""
    if target_q["type"] == "GOLDEN": inv["golden_candy"] = inv.get("golden_candy", 0) + 1; msg = "獲得 ✨ 黃金糖果 x1"
    else: current_user.money += target_q["gold"]; current_user.exp += target_q["xp"]; current_user.pet_exp += target_q["xp"]; msg = f"獲得 {target_q['gold']}G, {target_q['xp']} XP"
    
    # 移除並補新
    quests = [q for q in quests if q["id"] != qid]
    new_q = generate_quests(current_user.level, count=1)[0]
    quests.append(new_q)
    
    current_user.quests = json.dumps(quests); current_user.inventory = json.dumps(inv); db.commit()
    return {"message": msg}

# ----------------- 戰鬥與其他 -----------------

@router.post("/wild/attack")
async def wild_attack_api(is_win: bool = Query(...), is_powerful: bool = Query(False), target_name: str = Query("野怪"), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if is_win:
        xp = current_user.level * 20; money = current_user.level * 10
        current_user.exp += xp; current_user.pet_exp += xp; current_user.money += money
        msg = f"獲得 {xp} XP, {money} G"
        if is_powerful:
            inv = json.loads(current_user.inventory); inv["growth_candy"] = inv.get("growth_candy", 0) + 1; current_user.inventory = json.dumps(inv); msg += " & 🍬 成長糖果 x1"
        
        # 任務進度更新 (比對名稱)
        quests = json.loads(current_user.quests) if current_user.quests else []
        quest_updated = False
        for q in quests:
            if q["status"] == "ACTIVE" and q.get("target") in target_name:
                q["now"] += 1
                if q["now"] >= q["req"]: q["status"] = "COMPLETED"
                quest_updated = True
        if quest_updated: current_user.quests = json.dumps(quests)

        box = json.loads(current_user.pokemon_storage)
        for p in box:
            if p["uid"] == current_user.active_pokemon_uid: p["exp"] = current_user.pet_exp; p["lv"] = current_user.pet_level; break
        current_user.pokemon_storage = json.dumps(box)
        db.commit()
        return {"message": f"勝利！{msg}"}
    return {"message": "戰鬥結束"}

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
    iv = random.randint(0, 100)
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
    current_user.pokemon_image = base["img"]
    current_user.pet_level = target["lv"]
    current_user.pet_exp = target["exp"]
    current_user.max_hp = apply_iv_stats_local(base["hp"], target["iv"], target["lv"])
    current_user.attack = apply_iv_stats_local(base["atk"], target["iv"], target["lv"])
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
        if inv.get("growth_candy", 0) < 1: raise HTTPException(status_code=400, detail="成長糖果不足")
        inv["growth_candy"] -= 1
        target["exp"] += 1000
        req = get_req_xp(target["lv"])
        while target["exp"] >= req and target["lv"] < 25:
            target["lv"] += 1; target["exp"] -= req; req = get_req_xp(target["lv"])
        if pokemon_uid == current_user.active_pokemon_uid:
            base = POKEDEX_DATA.get(target["name"])
            def apply_iv_stats_local(base_val, iv, level):
                iv_mult = 0.9 + (iv / 100) * 0.2
                return int(base_val * iv_mult * (1.06 ** (level - 1)))
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

async def check_levelup_dual(user: User):
    msg_list = []
    req_xp_player = get_req_xp(user.level)
    if user.exp >= req_xp_player and user.level < 25:
        user.level += 1
        user.exp -= req_xp_player
        msg_list.append(f"訓練師升級(Lv.{user.level})")
        await manager.broadcast(f"📢 恭喜玩家 [{user.username}] 提升到了 訓練師等級 {user.level}！")
    if (user.pet_level < user.level or (user.level == 1 and user.pet_level == 1)) and user.pet_level < 25:
        req_xp_pet = get_req_xp(user.pet_level)
        while user.pet_exp >= req_xp_pet:
            if user.pet_level >= user.level and user.level > 1: break
            if user.pet_level >= 25: break 
            user.pet_level += 1
            user.pet_exp -= req_xp_pet
            user.max_hp = int(user.max_hp * 1.08)
            user.hp = user.max_hp
            user.attack = int(user.attack * 1.06)
            msg_list.append(f"{user.pokemon_name}升級(Lv.{user.pet_level})")
            req_xp_pet = get_req_xp(user.pet_level)
    return " & ".join(msg_list) if msg_list else None

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
def get_raid_status():
    now = datetime.now()
    hour = now.hour
    is_raid_time = hour in [8, 18, 22] and now.minute < 30
    if is_raid_time and not RAID_STATE["active"]:
        bosses = ["急凍鳥", "火焰鳥", "閃電鳥"]
        name = bosses[hour % 3]
        RAID_STATE["active"] = True; RAID_STATE["boss_name"] = name; RAID_STATE["max_hp"] = 3000; RAID_STATE["hp"] = 3000; RAID_STATE["players"] = {}
    elif not is_raid_time: RAID_STATE["active"] = False
    return RAID_STATE

@router.post("/raid/join")
def join_raid(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not RAID_STATE["active"]: raise HTTPException(status_code=400, detail="目前沒有團體戰")
    if current_user.money < 1000: raise HTTPException(status_code=400, detail="入場費不足 1000G")
    current_user.money -= 1000; db.commit()
    RAID_STATE["players"][current_user.id] = {"name": current_user.username, "dmg": 0}
    return {"message": "已加入團體戰！"}

@router.post("/raid/attack")
async def attack_raid(damage: int = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not RAID_STATE["active"]: raise HTTPException(status_code=400, detail="團體戰已結束")
    if current_user.id not in RAID_STATE["players"]: raise HTTPException(status_code=400, detail="請先支付入場費")
    RAID_STATE["hp"] = max(0, RAID_STATE["hp"] - damage)
    RAID_STATE["players"][current_user.id]["dmg"] += damage
    await manager.broadcast(f"RAID_UPDATE|{RAID_STATE['hp']}|{RAID_STATE['max_hp']}")
    if RAID_STATE["hp"] <= 0:
        RAID_STATE["active"] = False; current_user.exp += 3000; current_user.pet_exp += 3000; db.commit()
        await manager.broadcast(f"RAID_WIN|{current_user.username}")
        return {"message": "Boss 擊敗！", "result": "WIN"}
    return {"message": "攻擊成功", "boss_hp": RAID_STATE["hp"]}