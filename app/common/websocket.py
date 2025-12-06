# app/common/websocket.py

from fastapi import WebSocket
from typing import List

class ConnectionManager:
    """
    這就是我們的「廣播站長」。
    他手上有一份名單，記錄了現在所有連線進來的玩家。
    """
    def __init__(self):
        # 存放所有連線中的玩家
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """玩家連線時，把他加入名單"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """玩家斷線時，把他移出名單"""
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """拿起大聲公，對所有人喊話"""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # 如果發送失敗（可能玩家剛好斷線），就忽略
                pass

# 建立一個「全域」的站長實例，讓大家共用
manager = ConnectionManager()