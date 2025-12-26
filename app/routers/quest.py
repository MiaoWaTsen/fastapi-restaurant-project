# app/routers/quest.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
import json
import uuid

from app.db.session import get_db
from app.models.user import User
from app.common.deps import get_current_user

router = APIRouter(prefix="/quests", tags=["quests"])

# 野怪解鎖表 (參考用)
WILD_UNLOCK_LEVELS_REF = {
    1: ["小拉達"], 2: ["波波"], 3: ["烈雀"], 4: ["阿柏蛇"], 5: ["瓦斯彈"],
    6: ["海星星"], 7: ["角金魚"], 8: ["走路草"], 9: ["穿山鼠"], 10: ["蚊香蝌蚪"],
    12: ["小磁怪"], 14: ["卡拉卡拉"], 16: ["喵喵"], 18: ["瑪瑙水母"], 20: ["海刺龍"]
}

# ==========================================
# A. 任務生成邏輯 (Generation)
# ==========================================
def generate_single_quest(pet_level: int):
    """
    生成單一任務：
    1. 決定類型 (3% 黃金 / 97% 一般)
    2. 決定目標 (根據 active_pet_level)
    3. 決定數量與獎勵
    """
    
    # 1. 篩選目標野怪 (Target Mob)
    # 邏輯：解鎖等級 <= 當前寵物等級
    targets_pool = []
    for u_lv, species in WILD_UNLOCK_LEVELS_REF.items():
        if u_lv <= pet_level:
            targets_pool.extend(species)
            
    # 防呆：如果等級太低沒有怪，預設給小拉達
    if not targets_pool:
        targets_pool = ["小拉達"]
    
    target_name = random.choice(targets_pool)
    
    # 2. 決定類型 (Type)
    # 3% 機率 -> 黃金任務
    is_golden = random.random() < 0.03 
    
    quest_id = str(uuid.uuid4())
    
    if is_golden:
        # ✨ 黃金任務設定
        # 數量：固定 5 隻
        # 獎勵：黃金糖果 (不給金幣經驗，或另外給，這裡依照您的需求設定為糖果)
        return {
            "id": quest_id,
            "type": "GOLDEN",         # 前端依此顯示金黃色背景
            "target": target_name,
            "target_display": f"✨ {target_name} (黃金)",
            "target_lv": pet_level,   # 紀錄生成時的等級
            "req": 5,
            "now": 0,                 # 當前進度
            "status": "IN_PROGRESS",  # 直接開始，無需接取
            "rewards": {
                "item": "golden_candy",
                "gold": 0,
                "xp": 0
            }
        }
    else:
        # 📜 一般任務設定
        # 數量：隨機 1 ~ 3 隻
        req_count = random.randint(1, 3)
        
        # 獎勵計算 (可自行調整係數)
        base_gold = 50
        base_xp = 30
        total_gold = req_count * base_gold
        total_xp = req_count * base_xp
        
        return {
            "id": quest_id,
            "type": "NORMAL",         # 前端依此顯示深色背景
            "target": target_name,
            "target_display": f"Lv.{pet_level} {target_name}",
            "target_lv": pet_level,
            "req": req_count,
            "now": 0,
            "status": "IN_PROGRESS",
            "rewards": {
                "item": None,
                "gold": total_gold,
                "xp": total_xp
            }
        }

def ensure_user_quests(user: User, slot_count=3):
    """
    確保使用者隨時有 3 個任務。
    若不足，依據當前 pet_level 補齊。
    """
    try:
        current_quests = json.loads(user.quests) if user.quests else []
    except:
        current_quests = []

    # 這裡假設 user.pet_level 就是「當前出戰寶可夢等級」
    # 如果您的 Active Pet 是存在另一個欄位，請在這裡修改，例如 user.active_pet_level
    active_level = user.pet_level if user.pet_level else 1
    
    if len(current_quests) < slot_count:
        needed = slot_count - len(current_quests)
        for _ in range(needed):
            new_q = generate_single_quest(active_level)
            current_quests.append(new_q)
        
        user.quests = json.dumps(current_quests)
        return True # 代表有更新
    return False

# ==========================================
# API Endpoints
# ==========================================

@router.get("/")
def get_quests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    取得任務列表。
    如果任務不滿 3 個，會自動補齊 (Refill)。
    """
    is_updated = ensure_user_quests(current_user)
    if is_updated:
        db.commit()
        db.refresh(current_user)
        
    return json.loads(current_user.quests)


# 這裡移除了 /accept API，因為按照您的邏輯，新任務是「補上空缺」並直接顯示進度條
# 所以不需要手動接取，直接是 IN_PROGRESS


@router.post("/abandon/{qid}")
def abandon_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    放棄任務 (需花費 1000 G)。
    放棄後，會「立即生成」一個新任務補上。
    """
    if current_user.money < 1000:
        raise HTTPException(status_code=400, detail="刪除任務需 1000 Gold")
    
    quests = json.loads(current_user.quests)
    
    # 找到並移除任務
    new_quests = [q for q in quests if q["id"] != qid]
    
    if len(new_quests) == len(quests):
        raise HTTPException(status_code=404, detail="找不到該任務")
    
    # 扣錢
    current_user.money -= 1000
    
    # 更新列表 (此時少一個)
    current_user.quests = json.dumps(new_quests)
    
    # 立即補位
    ensure_user_quests(current_user) # 這會補上一個新的
    
    db.commit()
    
    # 回傳最新的任務列表給前端重繪
    return {
        "message": "任務已刪除並刷新 (-1000G)", 
        "quests": json.loads(current_user.quests)
    }


@router.post("/claim/{qid}")
def claim_quest(qid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    C. 領取與刷新流程
    1. 驗證任務是否 COMPLETED
    2. 發放獎勵 (一般->錢/經驗, 黃金->糖果)
    3. 刪除舊任務
    4. 立即生成新任務補上
    """
    quests = json.loads(current_user.quests)
    # 注意：inventory 也要是 JSON 格式處理，假設 user.inventory 是一個 JSON string
    try:
        inv = json.loads(current_user.inventory) if current_user.inventory else {}
    except:
        inv = {}
    
    target_q = None
    target_index = -1
    
    # 1. 尋找任務
    for idx, q in enumerate(quests):
        if q["id"] == qid:
            target_q = q
            target_index = idx
            break
            
    if not target_q:
        raise HTTPException(status_code=404, detail="任務不存在")
        
    # 這裡判斷狀態：前端應該在 now >= req 時顯示領取按鈕
    # 後端做雙重驗證
    if target_q["now"] < target_q["req"]:
         raise HTTPException(status_code=400, detail="任務尚未完成，無法領取")
    
    # 2. 發放獎勵
    msg = ""
    rewards = target_q["rewards"]
    
    if target_q["type"] == "GOLDEN":
        # 黃金任務獎勵：黃金糖果
        current_candy = inv.get("golden_candy", 0)
        inv["golden_candy"] = current_candy + 1
        msg = "領取成功！獲得 ✨ 黃金糖果 x1"
    else:
        # 一般任務獎勵
        r_gold = rewards.get("gold", 0)
        r_xp = rewards.get("xp", 0)
        current_user.money += r_gold
        current_user.exp += r_xp
        current_user.pet_exp += r_xp # 假設同時給寵物經驗
        msg = f"領取成功！獲得 {r_gold}G, {r_xp} XP"
    
    # 3. 刪除該舊任務 (從列表中移除)
    quests.pop(target_index)
    
    # 更新 User 物件 (先存一次以免 ensure_user_quests 讀到舊的)
    current_user.quests = json.dumps(quests)
    current_user.inventory = json.dumps(inv)
    
    # 4. 立即生成新任務補位
    ensure_user_quests(current_user)
    
    db.commit()
    
    return {
        "message": msg,
        "quests": json.loads(current_user.quests) # 回傳最新列表供前端更新
    }