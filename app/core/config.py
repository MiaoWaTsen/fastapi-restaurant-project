# app/core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    
    # 你未來可以從 .env 增加更多設定
    # SECRET_KEY: str
    # ALGORITHM: str = "HS256"

    # --- 這一塊是關鍵 ---
    class Config:
        """
        這個子 Class 告訴 Pydantic 如何讀取設定
        """
        # 告訴 Pydantic：.env 檔案就在「執行指令的那個資料夾」
        env_file = ".env" 
    # --------------------

# 建立一個全域實例
settings = Settings()