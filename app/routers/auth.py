# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.db.session import get_db
# 確保匯入正確的 Model
from app.models.user import User, UserCreate, UserRead
# ⚠️ 關鍵：一定要從 security 匯入這兩個「函式」，不能直接用 pwd_context！
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# 1. 註冊 (Sign Up)
@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # --- 抓鬼用的 Log (除錯完可以刪掉) ---
    print(f"👀 收到註冊請求！帳號: {user.username}")
    print(f"👀 密碼原本長度: {len(user.password)}")
    # ----------------------------------

    # 檢查帳號是否重複
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # ⚠️ 關鍵：使用 get_password_hash (它會自動處理長度)，不要自己 hash！
    hashed_pw = get_password_hash(user.password)
    
    # 建立新玩家
    new_user = User(
        username=user.username, 
        hashed_password=hashed_pw,
        hp=200,      
        max_hp=200,
        attack=20    
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 2. 登入 (Login)
@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print(f"👀 嘗試登入：{form_data.username}")
    
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # ⚠️ 關鍵：使用 verify_password (它也會自動處理長度)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# 3. 查閱自己資料
@router.get("/me", response_model=UserRead)
def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user