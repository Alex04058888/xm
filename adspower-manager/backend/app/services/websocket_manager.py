"""
WebSocket连接管理器
"""
import json
import asyncio
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储所有活跃连接
        self.active_connections: Dict[str, WebSocket] = {}
        # 用户订阅的任务
        self.user_subscriptions: Dict[int, Set[str]] = {}  # user_id -> set of connection_ids
        # 任务订阅者
        self.task_subscribers: Dict[int, Set[str]] = {}  # task_id -> set of connection_ids
        
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: int):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        # 初始化用户订阅
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        self.user_subscriptions[user_id].add(connection_id)
        
        logger.info(
            "WebSocket connected",
            connection_id=connection_id,
            user_id=user_id,
            total_connections=len(self.active_connections)
        )
        
        # 发送连接成功消息
        await self.send_personal_message(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    def disconnect(self, connection_id: str, user_id: int):
        """断开WebSocket连接"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # 清理用户订阅
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(connection_id)
            if not self.user_subscriptions[user_id]:
                del self.user_subscriptions[user_id]
        
        # 清理任务订阅
        for task_id, subscribers in self.task_subscribers.items():
            subscribers.discard(connection_id)
        
        # 清理空的任务订阅
        empty_tasks = [task_id for task_id, subscribers in self.task_subscribers.items() if not subscribers]
        for task_id in empty_tasks:
            del self.task_subscribers[task_id]
        
        logger.info(
            "WebSocket disconnected",
            connection_id=connection_id,
            user_id=user_id,
            total_connections=len(self.active_connections)
        )
    
    async def send_personal_message(self, connection_id: str, message: Dict[str, Any]):
        """发送个人消息"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(
                    "Failed to send personal message",
                    connection_id=connection_id,
                    error=str(e)
                )
                # 连接可能已断开，清理连接
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
    
    async def send_to_user(self, user_id: int, message: Dict[str, Any]):
        """发送消息给指定用户的所有连接"""
        if user_id in self.user_subscriptions:
            connection_ids = list(self.user_subscriptions[user_id])
            for connection_id in connection_ids:
                await self.send_personal_message(connection_id, message)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """广播消息给所有连接"""
        if self.active_connections:
            connection_ids = list(self.active_connections.keys())
            for connection_id in connection_ids:
                await self.send_personal_message(connection_id, message)
    
    def subscribe_to_task(self, connection_id: str, task_id: int):
        """订阅任务更新"""
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        self.task_subscribers[task_id].add(connection_id)
        
        logger.info(
            "Subscribed to task",
            connection_id=connection_id,
            task_id=task_id
        )
    
    def unsubscribe_from_task(self, connection_id: str, task_id: int):
        """取消订阅任务更新"""
        if task_id in self.task_subscribers:
            self.task_subscribers[task_id].discard(connection_id)
            if not self.task_subscribers[task_id]:
                del self.task_subscribers[task_id]
        
        logger.info(
            "Unsubscribed from task",
            connection_id=connection_id,
            task_id=task_id
        )
    
    async def send_task_update(self, task_id: int, update: Dict[str, Any]):
        """发送任务更新给订阅者"""
        if task_id in self.task_subscribers:
            message = {
                "type": "task_update",
                "task_id": task_id,
                "data": update,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            connection_ids = list(self.task_subscribers[task_id])
            for connection_id in connection_ids:
                await self.send_personal_message(connection_id, message)
    
    async def send_system_notification(self, user_id: int, notification: Dict[str, Any]):
        """发送系统通知"""
        message = {
            "type": "system_notification",
            "data": notification,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_to_user(user_id, message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            "total_connections": len(self.active_connections),
            "total_users": len(self.user_subscriptions),
            "total_task_subscriptions": len(self.task_subscribers),
            "connections_per_user": {
                user_id: len(connections) 
                for user_id, connections in self.user_subscriptions.items()
            }
        }


# 全局连接管理器实例
connection_manager = ConnectionManager()


class TaskUpdateNotifier:
    """任务更新通知器"""
    
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
    
    async def notify_task_started(self, task_id: int, task_data: Dict[str, Any]):
        """通知任务开始"""
        await self.manager.send_task_update(task_id, {
            "status": "started",
            "task": task_data
        })
    
    async def notify_task_progress(self, task_id: int, progress: int, current_node: int, message: str = None):
        """通知任务进度"""
        await self.manager.send_task_update(task_id, {
            "status": "progress",
            "progress": progress,
            "current_node": current_node,
            "message": message
        })
    
    async def notify_task_completed(self, task_id: int, result: Dict[str, Any]):
        """通知任务完成"""
        await self.manager.send_task_update(task_id, {
            "status": "completed",
            "result": result
        })
    
    async def notify_task_failed(self, task_id: int, error: str, node_index: int = None):
        """通知任务失败"""
        await self.manager.send_task_update(task_id, {
            "status": "failed",
            "error": error,
            "error_node_index": node_index
        })
    
    async def notify_task_log(self, task_id: int, log_entry: Dict[str, Any]):
        """通知任务日志"""
        await self.manager.send_task_update(task_id, {
            "status": "log",
            "log": log_entry
        })


# 全局任务通知器实例
task_notifier = TaskUpdateNotifier(connection_manager)


async def handle_websocket_message(connection_id: str, user_id: int, message: Dict[str, Any]):
    """处理WebSocket消息"""
    message_type = message.get("type")
    
    if message_type == "subscribe_task":
        task_id = message.get("task_id")
        if task_id:
            connection_manager.subscribe_to_task(connection_id, task_id)
            await connection_manager.send_personal_message(connection_id, {
                "type": "subscription_confirmed",
                "task_id": task_id
            })
    
    elif message_type == "unsubscribe_task":
        task_id = message.get("task_id")
        if task_id:
            connection_manager.unsubscribe_from_task(connection_id, task_id)
            await connection_manager.send_personal_message(connection_id, {
                "type": "unsubscription_confirmed",
                "task_id": task_id
            })
    
    elif message_type == "ping":
        await connection_manager.send_personal_message(connection_id, {
            "type": "pong",
            "timestamp": asyncio.get_event_loop().time()
        })
    
    elif message_type == "get_stats":
        stats = connection_manager.get_connection_stats()
        await connection_manager.send_personal_message(connection_id, {
            "type": "stats",
            "data": stats
        })
    
    else:
        logger.warning(
            "Unknown WebSocket message type",
            connection_id=connection_id,
            user_id=user_id,
            message_type=message_type
        )
