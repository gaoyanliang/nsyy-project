import logging
from typing import List, Dict
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # 窗口ID -> WebSocket 列表（支持多连接）
        self.window_connections: Dict[int, List[WebSocket]] = {}
        # 大屏展示连接（单例，但可以改成列表）
        self.display_connections: List[WebSocket] = []
        # 取药连接
        self.pharmacy_connections: List[WebSocket] = []

    async def connect_window(self, websocket: WebSocket, window_id: int):
        """接受窗口WebSocket连接"""
        await websocket.accept()
        # 清理该窗口下已失效的连接
        self._clean_window_connections(window_id)
        if window_id not in self.window_connections:
            self.window_connections[window_id] = []
        self.window_connections[window_id].append(websocket)
        logger.info(f"窗口 {window_id} 新连接，当前连接数: {len(self.window_connections[window_id])}")

    async def connect_display(self, websocket: WebSocket):
        await websocket.accept()
        self.display_connections.append(websocket)

    async def connect_pharmacy(self, websocket: WebSocket):
        await websocket.accept()
        self.pharmacy_connections.append(websocket)

    def _clean_window_connections(self, window_id: int):
        """移除该窗口下所有已关闭的连接"""
        if window_id not in self.window_connections:
            return
        alive = []
        for ws in self.window_connections[window_id]:
            # 检查连接是否仍然活跃
            if ws.client_state == WebSocketState.CONNECTED:
                alive.append(ws)
            else:
                logger.debug(f"移除窗口 {window_id} 失效连接")
        if len(alive) != len(self.window_connections[window_id]):
            self.window_connections[window_id] = alive

    def disconnect_window(self, websocket: WebSocket, window_id: int):
        """移除指定窗口的指定连接"""
        if window_id not in self.window_connections:
            return
        # 移除该 websocket 对象
        self.window_connections[window_id] = [
            ws for ws in self.window_connections[window_id] if ws != websocket
        ]
        if not self.window_connections[window_id]:
            del self.window_connections[window_id]
        logger.info(f"窗口 {window_id} 连接断开，剩余连接数: {len(self.window_connections.get(window_id, []))}")

    def disconnect_display(self, websocket: WebSocket):
        if websocket in self.display_connections:
            self.display_connections.remove(websocket)

    def disconnect_pharmacy(self, websocket: WebSocket):
        if websocket in self.pharmacy_connections:
            self.pharmacy_connections.remove(websocket)


    # ---------- 发送消息 ----------
    async def send_to_window(self, window_id: int, message: dict):
        """向指定窗口的所有活跃连接发送消息"""
        if window_id not in self.window_connections:
            return
        # 惰性清理，移除失效连接
        self._clean_window_connections(window_id)
        if window_id not in self.window_connections:
            return
        for ws in self.window_connections[window_id]:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"向窗口 {window_id} 发送失败: {e}，移除该连接")
                # 从列表中移除该连接
                self.window_connections[window_id] = [
                    w for w in self.window_connections[window_id] if w != ws
                ]
        # 若列表为空则删除键
        if not self.window_connections.get(window_id):
            del self.window_connections[window_id]

    async def broadcast_to_display(self, message: dict):
        """广播给所有大屏连接"""
        for ws in self.display_connections[:]:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"广播给大屏失败: {e}")
                self.display_connections.remove(ws)

    async def broadcast_to_pharmacy(self, message: dict):
        for ws in self.pharmacy_connections[:]:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"广播给药房失败: {e}")
                self.pharmacy_connections.remove(ws)

    async def broadcast_all(self, message: dict):
        """广播给所有连接（窗口、大屏、药房）"""
        # 向所有窗口发送
        for window_id in list(self.window_connections.keys()):
            await self.send_to_window(window_id, message)
        await self.broadcast_to_display(message)
        await self.broadcast_to_pharmacy(message)





manager = ConnectionManager()