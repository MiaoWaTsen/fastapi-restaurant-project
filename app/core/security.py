# app/core/security.py

from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
import hashlib  # <--- 關鍵：用來解決密碼過長的問題

# --- 設定區 (正式上線建議改用環境變數讀取) ---
SECRET_KEY = "CHANGE_THIS_TO_A_SUPER_SECRET_KEY"  # 請換成你自己隨便打的一長串亂碼
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token 有效期 30 分鐘

# 設定密碼加密方式為 bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- 核心工具函式 ---

def _hash_if_long(password: str) -> str:
    """
    Bcrypt 有一個硬性限制：密碼不能超過 72 bytes。
    為了避免使用者輸入長密碼導致伺服器崩潰，
    如果密碼太長，我們先用 SHA256 把它壓縮成固定的 64 字元長度。
    """
    if len(password) > 72:
        # 使用 SHA256 雜湊，將長密碼轉換為 64 字元的十六進位字串
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    return password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # 🔥 修正：Bcrypt 有 72 bytes 限制，過長的密碼會導致崩潰
    # 我們先將密碼轉為 bytes，如果超過 71 bytes 就截斷
    # (保留 1 byte 給 null terminator，雖然 python 不一定需要，但保險起見)
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 71:
        # 如果密碼太長，這裡做截斷處理。
        # 注意：這在資安上是可接受的妥協，因為攻擊者必須猜對前 71 個字元
        plain_password = password_bytes[:71].decode('utf-8', errors='ignore')
        
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    # 同樣地，雜湊時也要截斷
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 71:
        password = password_bytes[:71].decode('utf-8', errors='ignore')
        
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    """
    製作 JWT 識別證 (Token)
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt