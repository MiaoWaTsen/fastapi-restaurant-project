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

# 完整圖鑑 (補齊缺漏的野怪，防止 500 錯誤)
POKEDEX_DATA = {
    "小拉達": {"hp": 90, "atk": 80, "img": "https://img.pokemondb.net/artwork/large/rattata.jpg"},
    "波波": {"hp": 95, "atk": 85, "img": "https://img.pokemondb.net/artwork/large/pidgey.jpg"},
    "烈雀": {"hp": 90, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/spearow.jpg"},
    "阿柏蛇": {"hp": 100, "atk": 95, "img": "https://img.pokemondb.net/artwork/large/ekans.jpg"},
    "瓦斯彈": {"hp": 110, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/koffing.jpg"},
    "走路草": {"hp": 100, "atk": 85, "img": "https://img.pokemondb.net/artwork/large/oddish.jpg"},
    "海星星": {"hp": 100, "atk": 100, "img": "https://img.pokemondb.net/artwork/large/staryu.jpg"},
    "角金魚": {"hp": 110, "atk": 95, "img": "https://img.pokemondb.net/artwork/large/goldeen.jpg"},
    "穿山鼠": {"hp": 120, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/sandshrew.jpg"},
    "喵喵": {"hp": 90, "atk": 95, "img": "https://img.pokemondb.net/artwork/large/meowth.jpg"},
    "小磁怪": {"hp": 95, "atk": 105, "img": "https://img.pokemondb.net/artwork/large/magnemite.jpg"},
    "卡拉卡拉": {"hp": 110, "atk": 100, "img": "https://img.pokemondb.net/artwork/large/cubone.jpg"},
    "蚊香勇士": {"hp": 160, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/poliwrath.jpg"},
    "暴鯉龍": {"hp": 180, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/gyarados.jpg"},
    
    # 御三家與其他
    "妙蛙種子": {"hp": 130, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg"},
    "小火龍": {"hp": 112, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/charmander.jpg"},
    "傑尼龜": {"hp": 121, "atk": 121, "img": "https://img.pokemondb.net/artwork/large/squirtle.jpg"},
    "妙蛙花": {"hp": 152, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/venusaur.jpg"},
    "噴火龍": {"hp": 130, "atk": 152, "img": "https://img.pokemondb.net/artwork/large/charizard.jpg"},
    "水箭龜": {"hp": 141, "atk": 141, "img": "https://img.pokemondb.net/artwork/large/blastoise.jpg"},
    "毛辮羊": {"hp": 120, "atk": 120, "img": "https://img.pokemondb.net/artwork/large/wooloo.jpg"},
    "皮卡丘": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/pikachu.jpg"},
    "伊布": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/eevee.jpg"},
    "胖丁": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/jigglypuff.jpg"},
    "皮皮": {"hp": 125, "atk": 125, "img": "https://img.pokemondb.net/artwork/large/clefairy.jpg"},
    "大蔥鴨": {"hp": 120, "atk": 130, "img": "https://img.pokemondb.net/artwork/large/farfetchd.jpg"},
    "呆呆獸": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/slowpoke.jpg"},
    "可達鴨": {"hp": 122, "atk": 122, "img": "https://img.pokemondb.net/artwork/large/psyduck.jpg"},
    "卡比獸": {"hp": 175, "atk": 112, "img": "https://img.pokemondb.net/artwork/large/snorlax.jpg"},
    "吉利蛋": {"hp": 220, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/chansey.jpg"},
    "幸福蛋": {"hp": 230, "atk": 90, "img": "https://img.pokemondb.net/artwork/large/blissey.jpg"},
    "拉普拉斯": {"hp": 165, "atk": 140, "img": "https://img.pokemondb.net/artwork/large/lapras.jpg"},
    "快龍":   {"hp": 150, "atk": 148, "img": "https://img.pokemondb.net/artwork/large/dragonite.jpg"},
    "急凍鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/articuno.jpg"},
    "火焰鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/moltres.jpg"},
    "閃電鳥": {"hp": 150, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/zapdos.jpg"},
    "超夢":   {"hp": 152, "atk": 155, "img": "https://img.pokemondb.net/artwork/large/mewtwo.jpg"},
    "夢幻":   {"hp": 155, "atk": 150, "img": "https://img.pokemondb.net/artwork/large/mew.jpg"}
}

# 扭蛋池
GACHA_NORMAL = [{"name": "妙蛙種子", "rate": 5}, {"name": "小火龍", "rate": 5}, {"name": "傑尼龜", "rate": 5}, {"name": "伊布", "rate": 8}, {"name": "皮卡丘", "rate": 8}, {"name": "皮皮", "rate": 10}, {"name": "胖丁", "rate": 10}, {"name": "毛辮羊", "rate": 8}, {"name": "大蔥鴨", "rate": 12}, {"name": "呆呆獸", "rate": 12}, {"name": "可達鴨", "rate": 12}, {"name": "卡比獸", "rate": 2}, {"name": "吉利蛋", "rate": 2}]
GACHA_MEDIUM = [{"name": "妙蛙種子", "rate": 10}, {"name": "小火龍", "rate": 10}, {"name": "傑尼龜", "rate": 10}, {"name": "伊布", "rate": 10}, {"name": "皮卡丘", "rate": 10}, {"name": "呆呆獸", "rate": 10}, {"name": "可達鴨", "rate": 10}, {"name": "毛辮羊", "rate": 10}, {"name": "卡比獸", "rate": 5}, {"name": "吉利蛋", "rate": 3}, {"name": "拉普拉斯", "rate": 3}, {"name": "妙蛙花", "rate": 3}, {"name": "噴火龍", "rate": 3}, {"name": "水箭龜", "rate": 3}]
GACHA_HIGH = [{"name": "卡比獸", "rate": 20}, {"name": "吉利蛋", "rate": 24}, {"name": "幸福蛋", "rate": 10}, {"name": "拉普拉斯", "rate": 10}, {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10}, {"name": "快龍", "rate": 6}]
GACHA_CANDY = [{"name": "伊布", "rate": 20}, {"name": "皮卡丘", "rate": 20}, {"name": "妙蛙花", "rate": 10}, {"name": "噴火龍", "rate": 10}, {"name": "水箭龜", "rate": 10}, {"name": "卡比獸", "rate": 10}, {"name": "吉利蛋", "rate": 10}, {"name": "幸福蛋", "rate": 4}, {"name": "拉普拉斯", "rate": 3}, {"name": "快龍", "rate": 3}]
GACHA_GOLDEN = [{"name": "卡比獸", "rate": 30}, {"name": "吉利蛋", "rate": 35}, {"name": "幸福蛋", "rate": 20}, {"name": "拉普拉斯", "rate": 10}, {"name": "快龍", "rate": 5}]

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
    
    new_mon = { "uid": str(uuid.uuid4()), "name": prize_name, "iv": random.randint(0, 100), "lv": 1, "exp": 0 }
    box.append(new_mon)
    current_user.pokemon_storage = json.dumps(box)
    current_user.inventory = json.dumps(inventory)
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    if prize_name not in unlocked: unlocked.append(prize_name); current_user.unlocked_monsters = ",".join(unlocked)
    db.commit()
    if gacha_type in ['golden', 'high'] or prize_name in ['快龍', '超夢', '夢幻', '拉普拉斯', '幸福蛋']:
        await manager.broadcast(f"🎰 恭喜 [{current_user.username}] 獲得了稀有的 [{prize_name}]！")
    return {"message": f"獲得 {prize_name} (IV: {new_mon['iv']})!", "prize": new_mon, "user": current_user}

@router.post("/box/swap/{pokemon_uid}")
async def swap_active_pokemon(pokemon_uid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage)
    target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到")
    current_user.active_pokemon_uid = pokemon_uid
    current_user.pokemon_name = target["name"]
    base = POKEDEX_DATA.get(target["name"])
    current_user.pokemon_image = base["img"]
    current_user.pet_level = target["lv"]
    current_user.pet_exp = target["exp"]
    current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], True)
    current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], True)
    current_user.hp = current_user.max_hp
    db.commit()
    msg = f"EVENT:PVP_SWAP|{current_user.id}|{target['name']}|{base['img']}|{current_user.hp}|{current_user.max_hp}|{current_user.attack}"
    await manager.broadcast(msg)
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
            target["lv"] += 1
            target["exp"] -= req
            req = get_req_xp(target["lv"])
        if pokemon_uid == current_user.active_pokemon_uid:
            current_user.pet_level = target["lv"]
            current_user.pet_exp = target["exp"]
            base = POKEDEX_DATA.get(target["name"])
            current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], True)
            current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], True)
        msg = f"使用成長糖果，經驗+1000 (Lv.{target['lv']})"
    current_user.pokemon_storage = json.dumps(box)
    current_user.inventory = json.dumps(inv)
    db.commit()
    return {"message": msg, "user": current_user}

@router.post("/gamble")
async def gamble(amount: int = Query(..., gt=0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < amount: raise HTTPException(status_code=400, detail="金幣不足")
    if random.random() < 0.5:
        current_user.money += amount; msg = f"🎰 贏了！獲得 {amount} Gold！"
    else:
        current_user.money -= amount; msg = "💸 輸了... 沒關係下次再來！"
    db.commit()
    return {"message": msg, "money": current_user.money}

@router.post("/heal")
async def buy_heal(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.money < 50: raise HTTPException(status_code=400, detail="金幣不足")
    current_user.money -= 50
    current_user.hp = current_user.max_hp
    db.commit()
    return {"message": "體力已補滿"}

# 🔥 1. 野怪列表 API (修復版) 🔥
@router.get("/wild/list")
def get_wild_list(level: int, current_user: User = Depends(get_current_user)):
    wild_list = []
    
    # 確保野怪池內的名稱都在 POKEDEX_DATA 中
    common_names = ["小拉達", "波波", "烈雀", "阿柏蛇", "瓦斯彈", "走路草"]
    rare_names = ["海星星", "角金魚", "穿山鼠", "喵喵", "小磁怪", "卡拉卡拉"]
    
    names_pool = common_names
    if level >= 5: names_pool += rare_names
    if level >= 10: names_pool += ["蚊香勇士", "暴鯉龍"]
    
    for _ in range(6):
        try:
            name = random.choice(names_pool)
            # 防呆：如果名字不在圖鑑裡，回退到小拉達
            if name not in POKEDEX_DATA: name = "小拉達"
            
            base = POKEDEX_DATA[name] # 這裡讀取確保不報錯
            is_powerful = random.random() < 0.05
            mult = 1.2 if is_powerful else 1.0
            
            wild_hp = int(base["hp"] * 1.3 * mult * (1.09 ** (level - 1)))
            wild_atk = int(base["atk"] * 1.15 * mult * (1.07 ** (level - 1)))
            
            wild_list.append({
                "name": f"💪 {name}" if is_powerful else name,
                "raw_name": name,
                "is_powerful": is_powerful,
                "hp": wild_hp, "max_hp": wild_hp, "attack": wild_atk, "image_url": base["img"]
            })
        except Exception as e:
            print(f"Error generating wild mon: {e}")
            continue # 跳過錯誤
            
    return wild_list

# 🔥 2. 任務系統 (升級版) 🔥
def generate_quests(user_level):
    new_quests = []
    base_req = max(1, user_level)
    targets_pool = ["小拉達", "波波", "烈雀", "阿柏蛇", "瓦斯彈"]
    if user_level >= 5: targets_pool += ["海星星", "穿山鼠"]
    
    # 生成 3 個任務
    for _ in range(3):
        target = random.choice(targets_pool)
        count = random.randint(1, 3) + int(user_level/2)
        is_golden = random.random() < 0.15
        
        q = {
            "id": str(uuid.uuid4()),
            "type": "GOLDEN" if is_golden else "NORMAL",
            "target": target, # 明確指定怪獸名稱
            "target_lv": user_level,
            "req": count,
            "now": 0,
            "gold": count * 150,
            "xp": count * 80,
            "status": "WAITING"
        }
        if is_golden: q["gold"] = 0; q["xp"] = 0
        new_quests.append(q)
        
    return new_quests

@router.get("/quests/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quests = json.loads(current_user.quests) if current_user.quests else []
    
    # 如果任務少於3個，或者沒有進行中的任務，就補滿/重置
    active_count = len([q for q in quests if q["status"] in ["ACTIVE", "WAITING"]])
    if active_count < 3:
        # 簡單起見，如果不足就全部重置 (符合V2.0風格)
        quests = generate_quests(current_user.level)
        current_user.quests = json.dumps(quests)
        db.commit()
        
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
    new_quests = [q for q in quests if q["id"] != qid]
    
    if len(new_quests) == len(quests): raise HTTPException(status_code=404, detail="找不到任務")
    current_user.money -= 1000
    
    # 補一個新任務
    target = random.choice(["小拉達", "波波", "烈雀"])
    new_q = {
        "id": str(uuid.uuid4()), "type": "NORMAL", "target": target, "target_lv": current_user.level, 
        "req": 3, "now": 0, "gold": 300, "xp": 150, "status": "WAITING"
    }
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
    if target_q["type"] == "GOLDEN":
        inv["golden_candy"] = inv.get("golden_candy", 0) + 1; msg = "獲得 ✨ 黃金糖果 x1"
    else:
        current_user.money += target_q["gold"]; current_user.exp += target_q["xp"]; current_user.pet_exp += target_q["xp"]
        msg = f"獲得 {target_q['gold']}G, {target_q['xp']} XP"
        
    quests = [q for q in quests if q["id"] != qid] # 移除已完成
    # 補一個新的
    target = random.choice(["小拉達", "波波", "烈雀"])
    new_q = {
        "id": str(uuid.uuid4()), "type": "NORMAL", "target": target, "target_lv": current_user.level, 
        "req": 3, "now": 0, "gold": 300, "xp": 150, "status": "WAITING"
    }
    quests.append(new_q)
    
    current_user.quests = json.dumps(quests)
    current_user.inventory = json.dumps(inv)
    db.commit()
    return {"message": msg}

# 🔥 3. 戰鬥API (支援任務進度) 🔥
@router.post("/wild/attack")
async def wild_attack_api(
    is_win: bool = Query(...), 
    is_powerful: bool = Query(False), 
    target_name: str = Query("野怪"), # 新增參數：打倒了誰
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if is_win:
        xp = current_user.level * 20
        money = current_user.level * 10
        current_user.exp += xp
        current_user.pet_exp += xp
        current_user.money += money
        msg = f"獲得 {xp} XP, {money} G"
        if is_powerful:
            inv = json.loads(current_user.inventory)
            inv["growth_candy"] = inv.get("growth_candy", 0) + 1
            current_user.inventory = json.dumps(inv)
            msg += " & 🍬 成長糖果 x1"
        
        # 更新任務進度 (比對名稱)
        quests = json.loads(current_user.quests) if current_user.quests else []
        quest_updated = False
        for q in quests:
            if q["status"] == "ACTIVE":
                # 簡單比對：只要包含名稱就算 (例如 '💪 小拉達' 包含 '小拉達')
                if q["target"] in target_name: 
                    q["now"] += 1
                    if q["now"] >= q["req"]: q["status"] = "COMPLETED"
                    quest_updated = True
        if quest_updated: current_user.quests = json.dumps(quests)

        box = json.loads(current_user.pokemon_storage)
        for p in box:
            if p["uid"] == current_user.active_pokemon_uid:
                p["exp"] = current_user.pet_exp
                p["lv"] = current_user.pet_level
                break
        current_user.pokemon_storage = json.dumps(box)
        db.commit()
        return {"message": f"勝利！{msg}"}
    return {"message": "戰鬥結束"}

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
            current_user.exp += win_xp
            current_user.pet_exp += win_xp
            reward_msg = f"🏆 勝利！獲得 {win_xp} XP"
            if random.random() < 0.5:
                current_user.money += 200; reward_msg += " & 💰 200 G"
            else:
                inv = json.loads(current_user.inventory); inv["candy"] = inv.get("candy", 0) + 1; current_user.inventory = json.dumps(inv)
                reward_msg += " & 🍬 糖果 x1"
            lvl_msg = await check_levelup_dual(current_user)
            if lvl_msg: reward_msg += f" (升級!)"
            lose_xp = target.level * 10
            target.exp += lose_xp
            target.pet_exp += lose_xp
            await check_levelup_dual(target)
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
        RAID_STATE["active"] = True
        RAID_STATE["boss_name"] = name
        RAID_STATE["max_hp"] = 3000
        RAID_STATE["hp"] = 3000
        RAID_STATE["players"] = {}
    elif not is_raid_time:
        RAID_STATE["active"] = False
    return RAID_STATE

@router.post("/raid/join")
def join_raid(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not RAID_STATE["active"]: raise HTTPException(status_code=400, detail="目前沒有團體戰")
    if current_user.money < 1000: raise HTTPException(status_code=400, detail="入場費不足 1000G")
    current_user.money -= 1000
    db.commit()
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
        RAID_STATE["active"] = False
        current_user.exp += 3000
        current_user.pet_exp += 3000
        db.commit()
        await manager.broadcast(f"RAID_WIN|{current_user.username}")
        return {"message": "Boss 擊敗！", "result": "WIN"}
    return {"message": "攻擊成功", "boss_hp": RAID_STATE["hp"]}