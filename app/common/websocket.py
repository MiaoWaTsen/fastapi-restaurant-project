# app/common/websocket.py

from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # 存放活躍的連線: key=user_id, value=WebSocket
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        # 接受連線
        # 注意：accept() 通常在 endpoint 裡面做，這裡主要是記錄
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    def get_online_ids(self) -> List[int]:
        return list(self.active_connections.keys())

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message)
            except:
                self.disconnect(user_id)

    async def broadcast(self, message: str):
        # 對所有連線廣播
        # 為了避免迭代時字典大小改變報錯，先複製一份 keys
        for user_id in list(self.active_connections.keys()):
            try:
                ws = self.active_connections[user_id]
                await ws.send_text(message)
            except:
                self.disconnect(user_id)

manager = ConnectionManager()