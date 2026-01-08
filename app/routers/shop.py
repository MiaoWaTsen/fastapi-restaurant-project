# app/routers/shop.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, Column, Integer, String, ForeignKey, DateTime, Float, desc, text
from datetime import datetime, timedelta
import random
import json
import uuid
import re  # 用於解析任務描述

from app.db.session import get_db, engine
from app.db.base_class import Base 
from app.common.deps import get_current_user
from app.models.user import User, Gym
from app.common.websocket import manager 

# 引入完整的遊戲資料
from app.common.game_data import (
    SKILL_DB, POKEDEX_DATA, COLLECTION_MONS, OBTAINABLE_MONS, LEGENDARY_MONS,
    WILD_UNLOCK_LEVELS, GACHA_NORMAL, GACHA_MEDIUM, GACHA_HIGH, 
    GACHA_CANDY, GACHA_GOLDEN, GACHA_LEGENDARY_CANDY, GACHA_LEGENDARY_GOLD,
    LEVEL_XP_MAP, RAID_BOSS_POOL, get_req_xp, apply_iv_stats
)

router = APIRouter()

# =================================================================
# 🔥 初始化邏輯 (包含限制道館)
# =================================================================
def init_gyms():
    try:
        with Session(engine) as session:
            # 強制重建表格以確保欄位正確
            session.execute(text("DROP TABLE IF EXISTS gyms CASCADE"))
            session.commit()
            Base.metadata.create_all(bind=engine)
            
            # 建立道館 (含限制道館)
            gyms = [
                Gym(id=1, name="第一道館", buff_desc="防守方 HP/ATK +10%", income_rate=10),
                Gym(id=2, name="第二道館", buff_desc="防守方 HP/ATK +10%", income_rate=15),
                Gym(id=3, name="第三道館", buff_desc="防守方 HP/ATK +10%", income_rate=15),
                Gym(id=4, name="第四道館", buff_desc="防守方 HP/ATK +10%", income_rate=20),
                # 🔥 新增限制道館
                Gym(id=5, name="限制道館 A", buff_desc="⚠️ 限制 Lv.50 以下 | 收益 +25%", income_rate=25),
                Gym(id=6, name="限制道館 B", buff_desc="⚠️ 限制 Lv.50 以下 | 收益 +25%", income_rate=25),
            ]
            session.add_all(gyms)
            session.commit()
            print("✅ 道館初始化完成 (含限制道館)")
    except Exception as e:
        print(f"❌ 道館初始化錯誤: {e}")

# =================================================================
# 全域變數
# =================================================================
ONLINE_USERS = {}
INVITES = {}
DUEL_ROOMS = {}
GYM_BATTLES = {} 

# 每日團體戰時間表 (時, 分)
RAID_SCHEDULE = [(8, 0), (14, 0), (18, 0), (21, 0), (22, 0), (23, 0)] 
RAID_STATE = {"active": False, "status": "IDLE", "boss": None, "current_hp": 0, "max_hp": 0, "players": {}, "last_attack_time": None}

def update_user_activity(user_id):
    ONLINE_USERS[user_id] = datetime.utcnow()

def is_user_busy(user_id):
    for room in DUEL_ROOMS.values():
        if (room["p1"] == user_id or room["p2"] == user_id) and room["status"] != "ENDED":
            return True
    return False

def get_now_tw():
    return datetime.utcnow() + timedelta(hours=8)

@router.get("/data/skills")
def get_skills_data():
    return SKILL_DB

# =================================================================
# 1. 商店與扭蛋 API (含批量購買 & 盒子擴充)
# =================================================================
@router.post("/buy/{item_type}")
async def buy_item(item_type: str, count: int = Query(1, gt=0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    PRICES = {
        "candy": {"name": "神奇糖果", "price": 500, "key": "candy"},
        "growth": {"name": "成長糖果", "price": 2000, "key": "growth_candy"},
        "golden": {"name": "黃金糖果", "price": 10000, "key": "golden_candy"},
        "legendary": {"name": "傳說糖果", "price": 25000, "key": "legendary_candy"}
    }
    if item_type not in PRICES: raise HTTPException(status_code=400, detail="商品不存在")
    item = PRICES[item_type]
    cost = item["price"] * count # 計算總價
    
    if current_user.money < cost: raise HTTPException(status_code=400, detail=f"金幣不足！需要 {cost} G")
    current_user.money -= cost
    
    try: inv = json.loads(current_user.inventory)
    except: inv = {}
    inv[item["key"]] = inv.get(item["key"], 0) + count
    current_user.inventory = json.dumps(inv)
    db.commit()
    return {"message": f"購買成功！獲得 {item['name']} x{count}", "user": current_user}

@router.post("/gacha/{gacha_type}")
async def play_gacha(gacha_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try: box = json.loads(current_user.pokemon_storage) if current_user.pokemon_storage else []
    except: box = []
    
    # 🔥 盒子上限提升至 35
    if len(box) >= 35: raise HTTPException(status_code=400, detail="盒子滿了！請先放生")
    
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
        
    prize_data = random.choices(pool, weights=[p['weight'] for p in pool], k=1)[0]
    prize_name = prize_data['name']
    
    new_lv = random.randint(1, current_user.level)
    min_iv = 0
    if 'legendary' in gacha_type: min_iv = 60 
    iv = random.randint(min_iv, 100)
    
    new_mon = { "uid": str(uuid.uuid4()), "name": prize_name, "iv": iv, "lv": new_lv, "exp": 0 }
    box.append(new_mon)
    
    current_user.pokemon_storage = json.dumps(box)
    current_user.inventory = json.dumps(inventory)
    
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    if prize_name not in unlocked: unlocked.append(prize_name); current_user.unlocked_monsters = ",".join(unlocked)
    
    db.commit()
    try:
        if 'legendary' in gacha_type or gacha_type in ['golden', 'high'] or prize_name in ['快龍', '超夢', '夢幻', '拉普拉斯', '幸福蛋', '耿鬼', '鳳王', '洛奇亞']: 
            await manager.broadcast(f"🎰 恭喜 [{current_user.username}] 獲得了稀有的 [{prize_name}] (Lv.{new_lv})！")
    except: pass
    
    return {"message": f"獲得 {prize_name} (Lv.{new_lv}, IV: {iv})!", "prize": new_mon, "user": current_user}

# =================================================================
# 2. 核心功能 API (盒子、特訓、批量餵糖)
# =================================================================

@router.post("/box/swap/{pokemon_uid}")
async def swap_active_pokemon(pokemon_uid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try: box = json.loads(current_user.pokemon_storage)
    except: box = []
    target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到")
    
    current_user.active_pokemon_uid = pokemon_uid
    current_user.pokemon_name = target["name"]
    current_user.pet_level = target["lv"]
    current_user.pet_exp = target["exp"]
    
    base = POKEDEX_DATA.get(target["name"])
    if base:
        current_user.pokemon_image = base["img"]
        current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], is_hp=True, is_player=True)
        current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], is_hp=False, is_player=True)
    else:
        current_user.pokemon_image = "https://via.placeholder.com/150"
        current_user.max_hp = 100
        current_user.attack = 10
        
    current_user.hp = current_user.max_hp
    db.commit()
    await manager.broadcast(f"EVENT:PVP_SWAP|{current_user.id}")
    return {"message": f"就決定是你了，{target['name']}！"}

# 🔥 批量餵糖與放生
@router.post("/box/action/{action}/{pokemon_uid}")
async def box_action(action: str, pokemon_uid: str, count: int = Query(1, gt=0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage); inv = json.loads(current_user.inventory)
    target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到")
    
    if action == "release":
        if pokemon_uid == current_user.active_pokemon_uid: raise HTTPException(status_code=400, detail="無法放生出戰中寶可夢")
        box = [p for p in box if p["uid"] != pokemon_uid]
        if target["name"] in LEGENDARY_MONS:
            inv["legendary_candy"] = inv.get("legendary_candy", 0) + 1; msg = "✨ 放生傳說寶可夢，獲得 🔮 傳說糖果 x1"
        else: current_user.money += 100; msg = "放生成功，獲得 100 Gold"
        
    elif action == "candy":
        if target["lv"] >= current_user.level: raise HTTPException(status_code=400, detail="等級已達上限")
        if inv.get("growth_candy", 0) < count: raise HTTPException(status_code=400, detail="成長糖果不足")
        
        # 批量升級邏輯
        real_used = 0
        for _ in range(count):
            if target["lv"] >= current_user.level: break # 等級已滿，停止消耗
            inv["growth_candy"] -= 1
            target["exp"] += 1500 
            real_used += 1
            req = get_req_xp(target["lv"])
            while target["exp"] >= req and target["lv"] < 100:
                if target["lv"] >= current_user.level: break
                target["lv"] += 1; target["exp"] -= req; req = get_req_xp(target["lv"])
        
        if pokemon_uid == current_user.active_pokemon_uid:
            base = POKEDEX_DATA.get(target["name"])
            if base: current_user.pet_level = target["lv"]; current_user.pet_exp = target["exp"]; current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], is_hp=True, is_player=True); current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], is_hp=False, is_player=True)
        msg = f"使用了 {real_used} 顆糖果，目前 Lv.{target['lv']}"
        
    current_user.pokemon_storage = json.dumps(box); current_user.inventory = json.dumps(inv)
    db.commit()
    return {"message": msg, "user": current_user}

@router.post("/box/action/train")
async def train_pokemon(pokemon_uid: str, mode: str = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage)
    try: inv = json.loads(current_user.inventory)
    except: inv = {}
    target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到該寶可夢")
    is_legendary = target["name"] in LEGENDARY_MONS
    
    # 🔥 更新特訓費用 (V2.14.16 標準)
    cost_candy = 0; cost_gold_candy = 0; cost_leg_candy = 0; cost_money = 0
    if mode == 'normal':
        if is_legendary: 
            cost_candy = 50; cost_leg_candy = 3; cost_money = 5000
        else: 
            cost_candy = 30; cost_gold_candy = 3; cost_money = 1000
    elif mode == 'hyper':
        if is_legendary: 
            cost_candy = 250; cost_leg_candy = 15; cost_money = 25000
        else: 
            cost_candy = 150; cost_gold_candy = 15; cost_money = 5000
            
    if current_user.money < cost_money: raise HTTPException(status_code=400, detail=f"金幣不足")
    if inv.get("candy", 0) < cost_candy: raise HTTPException(status_code=400, detail=f"糖果不足")
    if inv.get("golden_candy", 0) < cost_gold_candy: raise HTTPException(status_code=400, detail=f"黃金糖果不足")
    if inv.get("legendary_candy", 0) < cost_leg_candy: raise HTTPException(status_code=400, detail=f"傳說糖果不足")
    
    current_user.money -= cost_money
    inv["candy"] -= cost_candy
    inv["golden_candy"] = inv.get("golden_candy", 0) - cost_gold_candy
    inv["legendary_candy"] = inv.get("legendary_candy", 0) - cost_leg_candy
    
    old_iv = target.get("iv", 0)
    
    # 一般特訓：傳說保底 60
    if mode == 'normal': 
        min_val = 60 if is_legendary else 0
        new_iv = random.randint(min_val, 100)
        msg = f"特訓完成！IV {old_iv} -> {new_iv}"
    else: 
        if old_iv >= 100: raise HTTPException(status_code=400, detail="IV 已滿")
        new_iv = random.randint(old_iv + 1, 100)
        msg = f"極限特訓成功！IV {old_iv} -> {new_iv}"
        
    target["iv"] = new_iv
    if pokemon_uid == current_user.active_pokemon_uid:
        base = POKEDEX_DATA.get(target["name"])
        if base: 
            current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], is_hp=True, is_player=True)
            current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], is_hp=False, is_player=True)
            current_user.hp = current_user.max_hp
    
    current_user.pokemon_storage = json.dumps(box)
    current_user.inventory = json.dumps(inv)
    db.commit()
    return {"message": msg, "iv": new_iv, "user": current_user}

# =================================================================
# 3. 道館系統 (Gym)
# =================================================================

@router.get("/gym/list")
def get_gym_list(db: Session = Depends(get_db)):
    try:
        gyms = db.query(Gym).all()
        if not gyms: raise Exception("No gyms found")
    except Exception as e:
        print(f"⚠️ 偵測到道館資料異常，正在嘗試自我修復... {e}")
        db.rollback()
        init_gyms() 
        return []
    result = []
    now = get_now_tw()
    for g in gyms:
        is_protected = False; remaining_protection = 0
        if g.protection_until and g.protection_until > now:
            is_protected = True; remaining_protection = int((g.protection_until - now).total_seconds())
        income_acc = 0
        if g.leader_id and g.occupied_at:
            mins = (now - g.occupied_at).total_seconds() / 60
            income_acc = int(mins * g.income_rate)
        result.append({
            "id": g.id, "name": g.name, "buff": g.buff_desc, "rate": g.income_rate,
            "leader_name": g.leader_name if g.leader_id else "無人佔領",
            "leader_img": g.leader_img if g.leader_id else "", "leader_id": g.leader_id,
            "is_protected": is_protected, "protection_sec": remaining_protection, "income_acc": income_acc
        })
    return result

@router.post("/gym/occupy/{gym_id}")
async def occupy_gym(gym_id: int, pokemon_uid: str = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    gym = db.query(Gym).filter(Gym.id == gym_id).first()
    if not gym: raise HTTPException(status_code=404, detail="道館不存在")
    if gym.leader_id and gym.leader_id != current_user.id: raise HTTPException(status_code=400, detail="道館已被佔領，請先擊敗館主")
    existing_gym = db.query(Gym).filter(Gym.leader_pokemon_uid == pokemon_uid).first()
    if existing_gym and existing_gym.id != gym_id: raise HTTPException(status_code=400, detail=f"這隻寶可夢正在守衛 {existing_gym.name}")
    try: box = json.loads(current_user.pokemon_storage)
    except: box = []
    target_mon = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target_mon: raise HTTPException(status_code=404, detail="找不到該寶可夢")
    if gym_id in [5, 6] and target_mon["lv"] > 50: raise HTTPException(status_code=400, detail="此道館限制 Lv.50 以下的寶可夢才能佔領！")
    base = POKEDEX_DATA.get(target_mon["name"])
    if not base: raise HTTPException(status_code=400, detail="資料錯誤")
    hp = apply_iv_stats(base["hp"], target_mon["iv"], target_mon["lv"], is_hp=True, is_player=True)
    atk = apply_iv_stats(base["atk"], target_mon["iv"], target_mon["lv"], is_hp=False, is_player=True)
    gym.leader_id = current_user.id; gym.leader_name = current_user.username; gym.leader_pokemon = target_mon["name"]; gym.leader_pokemon_uid = pokemon_uid; gym.leader_hp = hp; gym.leader_max_hp = hp; gym.leader_atk = atk; gym.leader_img = base["img"]; gym.occupied_at = get_now_tw(); gym.protection_until = get_now_tw() + timedelta(minutes=5)
    db.commit()
    return {"message": f"成功派遣 {target_mon['name']} 佔領 {gym.name}！"}

@router.post("/gym/battle/start/{gym_id}")
def start_gym_battle(gym_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gym = db.query(Gym).filter(Gym.id == gym_id).first()
    if not gym: raise HTTPException(status_code=404, detail="道館不存在")
    if not gym.leader_id: return {"result": "EMPTY", "message": "這是一個空道館，請選擇寶可夢佔領！"}
    if gym.leader_id == current_user.id:
        now = get_now_tw(); mins = (now - gym.occupied_at).total_seconds() / 60; income = int(mins * gym.income_rate)
        if income < 1: return {"result": "WAIT", "message": "目前收益太少，晚點再來收吧"}
        current_user.money += income; gym.occupied_at = now; db.commit()
        return {"result": "COLLECTED", "message": f"收取了 {income} Gold！"}
    if gym_id in [5, 6] and current_user.pet_level > 50: raise HTTPException(status_code=400, detail="此道館限制 Lv.50 以下的寶可夢才能挑戰！")
    now = get_now_tw()
    if gym.protection_until and gym.protection_until > now:
        left = int((gym.protection_until - now).total_seconds())
        raise HTTPException(status_code=400, detail=f"道館保護中，剩餘 {left} 秒")
    battle_id = str(uuid.uuid4())
    boss_hp = int(gym.leader_max_hp * 1.1); boss_atk = int(gym.leader_atk * 1.1)
    GYM_BATTLES[battle_id] = { 
        "gym_id": gym_id, "challenger_id": current_user.id, 
        "boss_data": { 
            "name": gym.leader_name, "pname": gym.leader_pokemon, 
            "hp": boss_hp, "max_hp": boss_hp, "atk": boss_atk, "img": gym.leader_img,
            "atk_mult": 1.0 
        },
        "player_atk_mult": 1.0 
    }
    return {"result": "BATTLE_START", "battle_id": battle_id, "opponent": GYM_BATTLES[battle_id]["boss_data"]}

@router.post("/gym/battle/attack/{battle_id}")
def gym_battle_attack(battle_id: str, damage: int = Query(0), heal: int = Query(0), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if battle_id not in GYM_BATTLES: raise HTTPException(status_code=404, detail="戰鬥已過期")
    room = GYM_BATTLES[battle_id]
    try: damage = int(damage)
    except: damage = 0
    if damage < 0: damage = 0
    
    # 玩家攻擊
    final_player_dmg = int(damage * room["player_atk_mult"])
    room["boss_data"]["hp"] = max(0, room["boss_data"]["hp"] - final_player_dmg)
    
    # 玩家補血 (先補)
    heal_val = 0
    final_user_hp = current_user.hp
    if heal > 0:
        heal_val = int(current_user.max_hp * 0.2)
        final_user_hp = min(current_user.max_hp, final_user_hp + heal_val)
    
    # Boss AI
    boss_dmg = 0
    if room["boss_data"]["hp"] > 0:
        boss_pname = room["boss_data"]["pname"]
        boss_base = POKEDEX_DATA.get(boss_pname, {})
        skills = boss_base.get("skills", ["撞擊", "撞擊", "撞擊"])
        chosen_skill = random.choice(skills)
        skill_info = SKILL_DB.get(chosen_skill, {"dmg": 20, "effect": None})
        
        base_atk = room["boss_data"]["atk"] * room["boss_data"]["atk_mult"]
        raw_dmg = (base_atk / 100) * skill_info["dmg"]
        boss_dmg = int(raw_dmg * random.uniform(0.95, 1.05))
        
        final_user_hp = max(0, final_user_hp - boss_dmg)
        
        effect = skill_info.get("effect"); prob = skill_info.get("prob", 0); val = skill_info.get("val", 0)
        if effect and random.random() < prob:
            if effect == "heal": h = int(room["boss_data"]["max_hp"] * val); room["boss_data"]["hp"] += h
            elif effect == "buff_atk": room["boss_data"]["atk_mult"] *= (1 + val)
            elif effect == "debuff_atk": room["player_atk_mult"] *= (1 - val)
            elif effect == "recoil": d = int(room["boss_data"]["max_hp"] * val); room["boss_data"]["hp"] = max(0, room["boss_data"]["hp"] - d)
    
    current_user.hp = final_user_hp
    db.commit()
    
    if room["boss_data"]["hp"] <= 0:
        gym = db.query(Gym).filter(Gym.id == room["gym_id"]).first()
        old_leader = db.query(User).filter(User.id == gym.leader_id).first()
        if old_leader:
            mins = (get_now_tw() - gym.occupied_at).total_seconds() / 60; income = int(mins * gym.income_rate); 
            if income > 0: old_leader.money += income
        gym.leader_id = None; gym.leader_name = ""; gym.leader_pokemon = ""; gym.leader_pokemon_uid = ""; gym.occupied_at = None; gym.protection_until = None
        current_user.hp = current_user.max_hp; current_user.money += 500; db.commit(); del GYM_BATTLES[battle_id]
        return {"result": "WIN_SELECT", "reward": "踢館成功！請選擇寶可夢佔領！", "user_hp": current_user.hp, "gym_id": gym.id}
    if current_user.hp <= 0: current_user.hp = current_user.max_hp; db.commit(); del GYM_BATTLES[battle_id]; return {"result": "LOSE", "reward": "挑戰失敗... (HP已回復)", "user_hp": current_user.hp, "boss_dmg": boss_dmg}
    return {"result": "NEXT", "boss_hp": room["boss_data"]["hp"], "user_hp": current_user.hp, "boss_dmg": boss_dmg, "real_heal_amt": heal_val}

@router.get("/pokedex/all")
def get_all_pokedex():
    result = []
    for name, data in POKEDEX_DATA.items():
        is_obtainable = name in OBTAINABLE_MONS
        result.append({ "name": name, "img": data["img"], "hp": data["hp"], "atk": data["atk"], "is_obtainable": is_obtainable })
    return result

@router.get("/pokedex/collection")
def get_pokedex_collection(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    try:
        box = json.loads(current_user.pokemon_storage) if current_user.pokemon_storage else []
        is_updated = False
        for p in box:
            if p['name'] not in unlocked: unlocked.append(p['name']); is_updated = True
        if is_updated: current_user.unlocked_monsters = ",".join(unlocked); db.commit()
    except: pass 
    result = []
    for name in COLLECTION_MONS:
        if name in POKEDEX_DATA:
            data = POKEDEX_DATA[name]
            result.append({ "name": name, "img": data["img"], "is_owned": name in unlocked })
    return result

@router.get("/leaderboard")
def get_leaderboard(type: str = "level", db: Session = Depends(get_db)):
    if type == "money":
        users = db.query(User).order_by(desc(User.money)).limit(10).all()
        return [{"rank": i+1, "username": u.username, "value": f"{u.money} G", "img": u.pokemon_image} for i, u in enumerate(users)]
    else: 
        users = db.query(User).order_by(desc(User.level)).limit(10).all()
        return [{"rank": i+1, "username": u.username, "value": f"Lv.{u.level}", "img": u.pokemon_image} for i, u in enumerate(users)]

# =================================================================
# 5. 團體戰與野外 API
# =================================================================

def update_raid_logic(db: Session = None):
    now = get_now_tw(); curr_total_mins = now.hour * 60 + now.minute
    for (h, m) in RAID_SCHEDULE:
        start_total_mins = h * 60 + m; start_lobby_mins = start_total_mins - 3 
        if start_lobby_mins < 0: start_lobby_mins += 1440
        if start_lobby_mins <= curr_total_mins < start_total_mins:
            if RAID_STATE["status"] != "LOBBY":
                boss_data = random.choices(RAID_BOSS_POOL, weights=[b['weight'] for b in RAID_BOSS_POOL], k=1)[0]
                RAID_STATE["active"] = True; RAID_STATE["status"] = "LOBBY"; RAID_STATE["boss"] = boss_data; RAID_STATE["max_hp"] = boss_data["hp"]; RAID_STATE["current_hp"] = boss_data["hp"]; RAID_STATE["players"] = {}; RAID_STATE["last_attack_time"] = get_now_tw()
            return
    for (h, m) in RAID_SCHEDULE:
        start_total_mins = h * 60 + m
        if 0 <= (curr_total_mins - start_total_mins) < 15:
            if RAID_STATE["status"] == "LOBBY": RAID_STATE["status"] = "FIGHTING"; RAID_STATE["last_attack_time"] = get_now_tw()
            elif RAID_STATE["status"] == "IDLE": 
                boss_data = random.choices(RAID_BOSS_POOL, weights=[b['weight'] for b in RAID_BOSS_POOL], k=1)[0]
                RAID_STATE["active"] = True; RAID_STATE["status"] = "FIGHTING"; RAID_STATE["boss"] = boss_data; RAID_STATE["max_hp"] = boss_data["hp"]; RAID_STATE["current_hp"] = boss_data["hp"]; RAID_STATE["players"] = {}; RAID_STATE["last_attack_time"] = get_now_tw()
            if RAID_STATE["status"] == "FIGHTING":
                last_time = RAID_STATE.get("last_attack_time")
                if last_time and (get_now_tw() - last_time).total_seconds() >= 7:
                    if db:
                        RAID_STATE["last_attack_time"] = get_now_tw(); base_dmg = int(RAID_STATE["boss"]["atk"] * 0.2); boss_dmg = int(base_dmg * random.uniform(0.95, 1.05))
                        active_uids = [uid for uid, p in RAID_STATE["players"].items() if not p.get("dead_at")]
                        if active_uids:
                            users_to_hit = db.query(User).filter(User.id.in_(active_uids)).all()
                            for u in users_to_hit: 
                                u.hp = max(0, u.hp - boss_dmg)
                                if u.hp <= 0:
                                    RAID_STATE["players"][u.id]["dead_at"] = get_now_tw().isoformat()
                            db.commit()
            if RAID_STATE["current_hp"] <= 0: RAID_STATE["status"] = "ENDED"
            return
    if RAID_STATE["status"] != "IDLE": RAID_STATE["active"] = False; RAID_STATE["status"] = "IDLE"; RAID_STATE["boss"] = None

@router.get("/raid/status")
def get_raid_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_raid_logic(db); my_status = {}; is_participant = False
    if current_user.id in RAID_STATE["players"]: my_status = RAID_STATE["players"][current_user.id]; is_participant = True
    boss_img = ""
    if RAID_STATE["boss"]: boss_img = RAID_STATE["boss"].get("img", "")
    return { "active": RAID_STATE["active"], "status": RAID_STATE["status"], "boss_name": RAID_STATE["boss"]["name"] if RAID_STATE["boss"] else "", "hp": RAID_STATE["current_hp"], "max_hp": RAID_STATE["max_hp"], "image": boss_img, "my_status": my_status, "user_hp": current_user.hp, "is_participant": is_participant }

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
def attack_raid_boss(damage: int = Query(0), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_raid_logic(db)
    if current_user.id not in RAID_STATE["players"]: raise HTTPException(status_code=400, detail="你不在大廳中")
    p_data = RAID_STATE["players"][current_user.id]
    if p_data.get("dead_at"): raise HTTPException(status_code=400, detail="你已死亡，請盡快復活！")
    if RAID_STATE["status"] != "FIGHTING": return {"message": "戰鬥尚未開始或已結束", "boss_hp": RAID_STATE["current_hp"]}
    try: damage = int(damage)
    except: damage = 0
    if damage < 0: damage = 0
    RAID_STATE["current_hp"] = max(0, RAID_STATE["current_hp"] - damage)
    return {"message": f"造成 {damage} 點傷害", "boss_hp": RAID_STATE["current_hp"]}

@router.post("/raid/recover")
def raid_recover(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    heal_amount = int(current_user.max_hp * 0.2); current_user.hp = min(current_user.max_hp, current_user.hp + heal_amount); db.commit()
    return {"message": f"回復了 {heal_amount} HP", "hp": current_user.hp}

@router.post("/raid/revive")
def revive_raid(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id not in RAID_STATE["players"]: raise HTTPException(status_code=400, detail="你不在大廳中")
    if current_user.money < 500: raise HTTPException(status_code=400, detail="金幣不足 500G")
    current_user.money -= 500; RAID_STATE["players"][current_user.id]["dead_at"] = None; current_user.hp = current_user.max_hp; db.commit()
    return {"message": "復活成功！"}

@router.post("/raid/claim")
def claim_raid_reward(choice: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if RAID_STATE["status"] != "ENDED": raise HTTPException(status_code=400, detail="戰鬥尚未結束")
    if current_user.id not in RAID_STATE["players"]: raise HTTPException(status_code=400, detail="你沒有參與這場戰鬥")
    p_data = RAID_STATE["players"][current_user.id]
    if p_data.get("claimed"): return {"message": "已經領過獎勵了"}
    weights = [20, 40, 40]; options = ["pet", "candy", "money"]; prize = random.choices(options, weights=weights, k=1)[0]; msg = ""
    try: inv = json.loads(current_user.inventory)
    except: inv = {}
    if prize == "candy": inv["legendary_candy"] = inv.get("legendary_candy", 0) + 1; msg = "獲得 🔮 傳說糖果 x1"
    elif prize == "money": current_user.money += 6000; msg = "獲得 💰 6000 Gold"
    elif prize == "pet":
        boss_name = RAID_STATE["boss"]["name"].split(" ")[1]; new_lv = random.randint(1, current_user.level)
        new_mon = { "uid": str(uuid.uuid4()), "name": boss_name, "iv": int(random.randint(60, 100)), "lv": new_lv, "exp": 0 }
        try: box = json.loads(current_user.pokemon_storage); box.append(new_mon); current_user.pokemon_storage = json.dumps(box); msg = f"獲得 Boss 寶可夢：{boss_name} (Lv.{new_lv})！"
        except: msg = "背包滿了，獲得 6000G 代替"; current_user.money += 6000
    RAID_STATE["players"][current_user.id]["claimed"] = True; current_user.inventory = json.dumps(inv)
    current_user.exp += 3000; current_user.pet_exp += 3000; current_user.hp = current_user.max_hp; db.commit()
    return {"message": msg, "prize": prize}

@router.get("/wild/list")
def get_wild_list(level: int, current_user: User = Depends(get_current_user)):
    update_user_activity(current_user.id); 
    if level > current_user.level: level = current_user.level
    target_level = level
    available_mons = []
    for unlock_lv, mons in WILD_UNLOCK_LEVELS.items():
        if unlock_lv <= target_level:
            available_mons.extend(mons)
    if not available_mons: available_mons = ["小拉達"]
    display_mons = available_mons 
    wild_list = []
    for name in display_mons:
        if name not in POKEDEX_DATA: continue
        base = POKEDEX_DATA[name]
        wild_hp = apply_iv_stats(base["hp"], 50, target_level, is_hp=True, is_player=False)
        wild_atk = apply_iv_stats(base["atk"], 50, target_level, is_hp=False, is_player=False)
        wild_skills = base.get("skills", ["撞擊", "撞擊", "撞擊"])
        wild_list.append({ "name": name, "raw_name": name, "is_powerful": False, "level": target_level, "hp": wild_hp, "max_hp": wild_hp, "attack": wild_atk, "image_url": base["img"], "skills": wild_skills })
    return wild_list

@router.post("/wild/attack")
async def wild_attack_api(is_win: bool = Query(...), is_powerful: bool = Query(False), target_name: str = Query("野怪"), target_level: int = Query(1), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    update_user_activity(current_user.id); current_user.hp = current_user.max_hp
    if is_win:
        real_name = target_name.replace("🔥 ", "").replace("強大的 ", "").replace("✨ ", "").strip()
        target_data = POKEDEX_DATA.get(real_name, POKEDEX_DATA.get("小拉達"))
        base_sum = target_data["hp"] + target_data["atk"]; xp = int((base_sum / 20) * target_level + 30); money = int(xp * 0.5) 
        current_user.exp += xp; current_user.pet_exp += xp; current_user.money += money; msg = f"獲得 {xp} XP, {money} G"
        inv = json.loads(current_user.inventory)
        if random.random() < 0.4: inv["candy"] = inv.get("candy", 0) + 1; msg += " & 🍬 獲得神奇糖果!"
        if is_powerful: inv["growth_candy"] = inv.get("growth_candy", 0) + 1; msg += " & 🍬 成長糖果 x1"
        current_user.inventory = json.dumps(inv)
        quests = json.loads(current_user.quests) if current_user.quests else []
        quest_updated = False
        for q in quests:
            if q["type"] in ["BATTLE_WILD", "GOLDEN"] and q["status"] != "COMPLETED":
                req_lv_match = re.search(r'Lv\.(\d+)', q.get("target_display", ""))
                req_lv = int(req_lv_match.group(1)) if req_lv_match else 1
                if q.get("target") in real_name and target_level >= req_lv:
                    q["now"] += 1
                    quest_updated = True
        if quest_updated: current_user.quests = json.dumps(quests)
        req_xp_p = get_req_xp(current_user.level)
        while current_user.exp >= req_xp_p and current_user.level < 100: current_user.exp -= req_xp_p; current_user.level += 1; req_xp_p = get_req_xp(current_user.level); msg += f" | 訓練師升級 Lv.{current_user.level}!"
        req_xp_pet = get_req_xp(current_user.pet_level)
        pet_leveled_up = False
        while current_user.pet_exp >= req_xp_pet and current_user.pet_level < 100: current_user.pet_exp -= req_xp_pet; current_user.pet_level += 1; req_xp_pet = get_req_xp(current_user.pet_level); pet_leveled_up = True; msg += f" | 寶可夢升級 Lv.{current_user.pet_level}!"
        try:
            box = json.loads(current_user.pokemon_storage); active_pet = next((p for p in box if p['uid'] == current_user.active_pokemon_uid), None)
            if active_pet:
                active_pet["exp"] = current_user.pet_exp; active_pet["lv"] = current_user.pet_level
                if pet_leveled_up:
                    base = POKEDEX_DATA.get(active_pet["name"])
                    if base: current_user.max_hp = apply_iv_stats(base["hp"], active_pet["iv"], current_user.pet_level, is_hp=True, is_player=True); current_user.attack = apply_iv_stats(base["atk"], active_pet["iv"], current_user.pet_level, is_hp=False, is_player=True); current_user.hp = current_user.max_hp
            current_user.pokemon_storage = json.dumps(box)
        except: pass
        db.commit()
        return {"message": f"勝利！HP已回復。{msg}"}
    db.commit()
    return {"message": "戰鬥結束，HP已回復。"}

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
    if is_user_busy(target_id): raise HTTPException(status_code=400, detail="對方忙錄中")
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
    if INVITES.get(current_user.id) != source_id: raise HTTPException(status_code=400, detail="無效邀請")
    room_id = str(uuid.uuid4())
    DUEL_ROOMS[room_id] = {
        "p1": source_id, "p2": current_user.id, "status": "PREPARING",
        "start_time": datetime.utcnow().isoformat(),
        "countdown_end": (datetime.utcnow() + timedelta(seconds=12)).isoformat(),
        "turn": None, "p1_data": None, "p2_data": None, "ended_at": None 
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
    keys_to_del = [k for k, r in DUEL_ROOMS.items() if r.get("ended_at") and (now - datetime.fromisoformat(r["ended_at"])).total_seconds() > 60]
    for k in keys_to_del: del DUEL_ROOMS[k]
    room = None
    for r in DUEL_ROOMS.values():
        if r["p1"] == current_user.id or r["p2"] == current_user.id:
            room = r; break
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
    if room["status"] in ["FIGHTING", "ENDED"]:
        is_p1 = (current_user.id == room["p1"])
        my_data = room["p1_data"] if is_p1 else room["p2_data"]
        op_data = room["p2_data"] if is_p1 else room["p1_data"]
        return {"status": room["status"], "room_id": "xxx", "turn": room["turn"], "my_data": my_data, "opponent_data": op_data, "is_my_turn": (room["turn"] == current_user.id)}
    return {"status": "NONE"}

@router.post("/duel/attack")
def duel_attack(damage: int = Query(0), heal: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    room = None
    for r in DUEL_ROOMS.values():
        if (r["p1"] == current_user.id or r["p2"] == current_user.id) and r["status"] == "FIGHTING":
            room = r; break
    if not room: raise HTTPException(status_code=404, detail="不在對戰中")
    if room["turn"] != current_user.id: raise HTTPException(status_code=400, detail="還沒輪到你")
    try: damage = int(damage)
    except: damage = 0
    if damage < 0: damage = 0
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
        room["status"] = "ENDED"; room["ended_at"] = datetime.utcnow().isoformat() 
        current_user.money += 300; current_user.exp += 500
        current_user.hp = current_user.max_hp; target_user.hp = target_user.max_hp
        db.commit()
        return {"result": "WIN", "reward": "獲得 300G & 500 XP"}
    room["turn"] = target_id
    db.commit()
    return {"result": "NEXT", "damage": damage, "heal": heal}

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

# 🔥 6. 新兌換碼
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
    elif code == "TRUW8Q3HD":
        inv["legendary_candy"] = inv.get("legendary_candy", 0) + 15
        msg = "兌換成功！獲得 🔮 傳說糖果 x15"; success = True
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
    try:
        db.delete(target)
        db.commit()
        return {"message": f"✅ 已成功刪除玩家 [{username}] 及其所有資料"}
    except Exception as e:
        db.rollback()
        return {"message": f"❌ 刪除失敗 (資料庫錯誤): {str(e)}"}