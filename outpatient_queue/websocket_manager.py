from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.window_connections: Dict[int, WebSocket] = {}  # 窗口ID -> WebSocket
        self.pharmacy_connections: List[WebSocket] = []  # 窗口ID -> WebSocket

    async def connect(self, websocket: WebSocket, connection_type: str = "display", window_id: int = None):
        await websocket.accept()
        if connection_type == "window" and window_id:
            self.window_connections[window_id] = websocket
        elif connection_type == "pharmacy":
            self.pharmacy_connections.append(websocket)
        else:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, window_id: int = None):
        if window_id and window_id in self.window_connections:
            del self.window_connections[window_id]
        elif websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """广播消息给所有大屏客户端"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

    async def send_to_window(self, window_id: int, message: dict):
        """发送消息给指定窗口"""
        if window_id in self.window_connections:
            try:
                await self.window_connections[window_id].send_json(message)
            except:
                pass

    async def broadcast_to_windows(self, message: dict):
        """广播消息给所有窗口"""
        for window_id, connection in self.window_connections.items():
            try:
                await connection.send_json(message)
            except:
                pass

    async def send_to_pharmacy(self, message: dict):
        """向所有取药页面连接发送消息"""
        for conn in self.pharmacy_connections:
            try:
                await conn.send_json(message)
            except Exception as e:
                pass


manager = ConnectionManager()