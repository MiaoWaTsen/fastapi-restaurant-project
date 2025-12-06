# app/common/websocket.py

from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # 改用 Dictionary: Key是玩家ID, Value是連線物件
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        # 登記名字：這位 user_id 上線了
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        # 劃掉名字
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def broadcast(self, message: str):
        # 對名冊裡的所有人發送
        for connection in self.active_connections.values():
            try:
                await connection.send_text(message)
            except:
                pass
    
    # 🔥 新增功能：查名冊，回傳現在誰在線上的 ID 列表
    def get_online_ids(self) -> List[int]:
        return list(self.active_connections.keys())

manager = ConnectionManager()