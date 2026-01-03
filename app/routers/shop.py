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

# 匯入資料檔 (請確保 app/common/game_data.py 存在)
from app.common.game_data import (
    SKILL_DB, POKEDEX_DATA, COLLECTION_MONS, OBTAINABLE_MONS,
    WILD_UNLOCK_LEVELS, GACHA_NORMAL, GACHA_MEDIUM, GACHA_HIGH, 
    GACHA_CANDY, GACHA_GOLDEN, GACHA_LEGENDARY_CANDY, GACHA_LEGENDARY_GOLD,
    LEVEL_XP_MAP, get_req_xp
)

router = APIRouter()

# 0. 強制檢查好友資料表
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
# 1. 數值計算公式 (V2.11.19 修正版)
# =================================================================
def apply_iv_stats(base_val, iv, level, is_hp=False, is_player=True):
    # 🔥 IV 影響範圍提升: 0.8 ~ 1.2
    iv_mult = 0.8 + (iv / 100) * 0.4
    
    if is_player:
        # 玩家成長: 攻 1.031, 血 1.03
        growth_rate = 1.03 if is_hp else 1.031
    else:
        # 🔥 野怪成長: 1.035 (後期更強)
        growth_rate = 1.035

    val = int(base_val * iv_mult * (growth_rate ** (level - 1)))
    return max(1, val) # 確保至少為 1，防止 0 導致 NaN

# ... (RAID Logic 不變) ...
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
def get_pokedex_collection(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    unlocked = current_user.unlocked_monsters.split(',') if current_user.unlocked_monsters else []
    try:
        box = json.loads(current_user.pokemon_storage) if current_user.pokemon_storage else []
        is_updated = False
        for p in box:
            if p['name'] not in unlocked:
                unlocked.append(p['name'])
                is_updated = True
        if is_updated:
            current_user.unlocked_monsters = ",".join(unlocked)
            db.commit()
    except: pass 
    result = []
    for name in COLLECTION_MONS:
        if name in POKEDEX_DATA:
            data = POKEDEX_DATA[name]
            result.append({ "name": name, "img": data["img"], "is_owned": name in unlocked })
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
        # 🔥 V2.11.19: 野怪成長公式 1.035
        wild_hp = int(buffed_base_hp * (1.035 ** (level - 1)))
        wild_atk = int(buffed_base_atk * (1.035 ** (level - 1)))
        wild_skills = base.get("skills", ["撞擊", "撞擊", "撞擊"])
        wild_list.append({ "name": name, "raw_name": name, "is_powerful": False, "level": level, "hp": wild_hp, "max_hp": wild_hp, "attack": wild_atk, "image_url": base["img"], "skills": wild_skills })
    return wild_list

@router.post("/wild/attack")
async def wild_attack_api(is_win: bool = Query(...), is_powerful: bool = Query(False), target_name: str = Query("野怪"), target_level: int = Query(1), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    update_user_activity(current_user.id)
    current_user.hp = current_user.max_hp
    if is_win:
        # 移除前綴以確保正確計算
        real_target_name = target_name.replace("🔥 強大的 ", "").replace("✨ ", "")
        target_data = POKEDEX_DATA.get(real_target_name, POKEDEX_DATA["小拉達"])
        
        base_stat_sum = target_data["hp"] + target_data["atk"]
        xp = int((base_stat_sum / 20) * target_level + 30)
        money = int(xp * 0.5) 
        current_user.exp += xp; current_user.pet_exp += xp; current_user.money += money
        msg = f"獲得 {xp} XP, {money} G"
        inv = json.loads(current_user.inventory)
        if random.random() < 0.4: inv["candy"] = inv.get("candy", 0) + 1; msg += " & 🍬 獲得神奇糖果!"
        if is_powerful: inv["growth_candy"] = inv.get("growth_candy", 0) + 1; msg += " & 🍬 成長糖果 x1"
        current_user.inventory = json.dumps(inv)
        
        quests = json.loads(current_user.quests) if current_user.quests else []
        quest_updated = False
        for q in quests:
            if q["type"] in ["BATTLE_WILD", "GOLDEN"] and q["status"] != "COMPLETED":
                if q.get("target") in real_target_name: 
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
                if base: 
                    # 🔥 升級時重新計算能力 (V2.11.19 修正公式)
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
    
    db.commit()
    try:
        if 'legendary' in gacha_type or gacha_type in ['golden', 'high'] or prize_name in ['快龍', '超夢', '夢幻', '拉普拉斯', '幸福蛋', '耿鬼', '鳳王', '洛奇亞']: await manager.broadcast(f"🎰 恭喜 [{current_user.username}] 獲得了稀有的 [{prize_name}] (Lv.{new_lv})！")
    except: pass
    return {"message": f"獲得 {prize_name} (Lv.{new_lv}, IV: {iv})!", "prize": new_mon, "user": current_user}

@router.post("/box/swap/{pokemon_uid}")
async def swap_active_pokemon(pokemon_uid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    box = json.loads(current_user.pokemon_storage); target = next((p for p in box if p["uid"] == pokemon_uid), None)
    if not target: raise HTTPException(status_code=404, detail="找不到")
    
    current_user.active_pokemon_uid = pokemon_uid
    current_user.pokemon_name = target["name"]
    current_user.pet_level = target["lv"]
    current_user.pet_exp = target["exp"]
    
    # 🔥 V2.11.19: 這裡會自動修復 NaN 和圖片問題
    # 直接查 POKEDEX_DATA 取得原始資料
    base = POKEDEX_DATA.get(target["name"])
    
    if base: 
        # 1. 寫入正確圖片
        current_user.pokemon_image = base["img"]
        # 2. 重新計算血量與攻擊 (絕對不會是 NaN)
        current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], is_hp=True, is_player=True)
        current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], is_hp=False, is_player=True)
    else: 
        # 防呆
        current_user.pokemon_image = "https://via.placeholder.com/150"
        current_user.max_hp = 100
        current_user.attack = 10

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
            if base: 
                current_user.pet_level = target["lv"]; current_user.pet_exp = target["exp"]; 
                current_user.max_hp = apply_iv_stats(base["hp"], target["iv"], target["lv"], is_hp=True, is_player=True); 
                current_user.attack = apply_iv_stats(base["atk"], target["iv"], target["lv"], is_hp=False, is_player=True)
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
    is_participant = False
    if current_user.id in RAID_STATE["players"]:
        my_status = RAID_STATE["players"][current_user.id]
        is_participant = True
        
    return {
        "active": RAID_STATE["active"],
        "status": RAID_STATE["status"],
        "boss_name": RAID_STATE["boss"]["name"] if RAID_STATE["boss"] else "",
        "hp": RAID_STATE["current_hp"],
        "max_hp": RAID_STATE["max_hp"],
        "image": RAID_STATE["boss"]["img"] if RAID_STATE["boss"] else "",
        "my_status": my_status,
        "user_hp": current_user.hp,
        "is_participant": is_participant
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
    
    weights = [20, 40, 40]
    options = ["pet", "candy", "money"]
    prize = random.choices(options, weights=weights, k=1)[0]
    
    msg = ""
    try:
        if not current_user.inventory: inv = {}
        else: inv = json.loads(current_user.inventory)
        if not isinstance(inv, dict): inv = {}
    except: inv = {}

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

# 🔥 V2.11.19: 簽到修復 (不依賴 DB 欄位)
@router.post("/social/daily_checkin")
def daily_checkin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        now = get_now_tw()
        today_str = now.strftime("%Y-%m-%d")
        
        # 讀取背包，若為空或格式錯誤則重置
        try:
            if not current_user.inventory: inv = {}
            else: inv = json.loads(current_user.inventory)
            if not isinstance(inv, dict): inv = {}
        except: 
            inv = {}

        # 檢查是否簽到過
        last_checkin = inv.get("last_checkin_date")
        if last_checkin == today_str:
            return {"message": "今天已經簽到過了"}
        
        prizes = ["1500G", "3000G", "candy", "golden", "8000G", "legendary"]
        weights = [30, 20, 20, 20, 6, 4]
        result = random.choices(prizes, weights=weights, k=1)[0]
        
        if current_user.money is None: current_user.money = 0
            
        msg = ""
        if result == "1500G": current_user.money += 1500; msg = "獲得 1500 Gold"
        elif result == "3000G": current_user.money += 3000; msg = "獲得 3000 Gold"
        elif result == "candy": inv["candy"] = inv.get("candy", 0) + 5; msg = "獲得 🍬 神奇糖果 x5"
        elif result == "golden": inv["golden_candy"] = inv.get("golden_candy", 0) + 1; msg = "獲得 ✨ 黃金糖果 x1"
        elif result == "8000G": current_user.money += 8000; msg = "大獎！獲得 💰 8000 Gold"
        elif result == "legendary": inv["legendary_candy"] = inv.get("legendary_candy", 0) + 1; msg = "超級大獎！獲得 🔮 傳說糖果 x1"
        
        # 寫入簽到日期
        inv["last_checkin_date"] = today_str
        current_user.inventory = json.dumps(inv)
        db.commit()
        return {"message": f"簽到成功！{msg}"}
    except Exception as e:
        print(f"Checkin Error: {str(e)}") 
        raise HTTPException(status_code=500, detail="簽到失敗")

@router.post("/social/add/{target_id}")
def add_friend(target_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if target_id == current_user.id: raise HTTPException(status_code=400, detail="不能加自己")
    target_user = db.query(User).filter(User.id == target_id).first()
    if not target_user: raise HTTPException(status_code=404, detail="找不到該玩家 ID") 
    
    try:
        existing = db.query(Friendship).filter(or_((Friendship.user_id == current_user.id) & (Friendship.friend_id == target_id), (Friendship.user_id == target_id) & (Friendship.friend_id == current_user.id))).first()
        if existing: return {"message": "已經是好友或已發送邀請"}
        
        new_fs = Friendship(user_id=current_user.id, friend_id=target_id, status="PENDING")
        db.add(new_fs)
        db.commit()
        return {"message": "已發送好友邀請"}
    except Exception as e:
        print(f"Add Friend Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="好友系統繁忙，請稍後再試")

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