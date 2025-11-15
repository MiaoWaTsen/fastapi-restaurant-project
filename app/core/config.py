# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    這個 class 會自動讀取 .env 檔案中的變數
    """
    DATABASE_URL: str

    # 你未來可以從 .env 增加更多設定，例如：
    # SECRET_KEY: str
    # ALGORITHM: str = "HS256"

    class Config:
        # 指定 .env 檔案的路徑
        # (因為 config.py 在 app/core/ 裡面，.env 在根目錄，所以要..兩次)
        env_file = "../../.env" 

# 建立一個全域實例，讓專案中其他檔案可以 import
settings = Settings()