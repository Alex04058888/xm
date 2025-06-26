"""
WebSocket API路由
"""
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.services.websocket_manager import connection_manager, handle_websocket_message
import structlog

logger = structlog.get_logger()

router = APIRouter()


async def get_current_user_ws(websocket: WebSocket, token: str, db: Session) -> User:
    """WebSocket认证"""
    try:
        user_id = verify_token(token, "access")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found or inactive")
            return None
        
        return user
    except Exception as e:
        logger.error("WebSocket authentication failed", error=str(e))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db)
):
    """WebSocket主端点"""
    
    # 认证用户
    user = await get_current_user_ws(websocket, token, db)
    if not user:
        return
    
    # 生成连接ID
    connection_id = str(uuid.uuid4())
    
    try:
        # 建立连接
        await connection_manager.connect(websocket, connection_id, user.id)
        
        # 发送欢迎消息
        await connection_manager.send_personal_message(connection_id, {
            "type": "welcome",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            },
            "connection_id": connection_id
        })
        
        # 监听消息
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                logger.info(
                    "WebSocket message received",
                    connection_id=connection_id,
                    user_id=user.id,
                    message_type=message.get("type")
                )
                
                # 处理消息
                await handle_websocket_message(connection_id, user.id, message)
                
            except json.JSONDecodeError:
                await connection_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(
                    "Error handling WebSocket message",
                    connection_id=connection_id,
                    error=str(e)
                )
                await connection_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Internal server error"
                })
    
    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected normally",
            connection_id=connection_id,
            user_id=user.id
        )
    except Exception as e:
        logger.error(
            "WebSocket connection error",
            connection_id=connection_id,
            user_id=user.id,
            error=str(e)
        )
    finally:
        # 清理连接
        connection_manager.disconnect(connection_id, user.id)


@router.websocket("/ws/tasks/{task_id}")
async def websocket_task_monitor(
    websocket: WebSocket,
    task_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """任务监控WebSocket端点"""
    
    # 认证用户
    user = await get_current_user_ws(websocket, token, db)
    if not user:
        return
    
    # 验证任务权限
    from app.models.task import Task
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user.id
    ).first()
    
    if not task:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Task not found")
        return
    
    # 生成连接ID
    connection_id = str(uuid.uuid4())
    
    try:
        # 建立连接
        await connection_manager.connect(websocket, connection_id, user.id)
        
        # 自动订阅任务更新
        connection_manager.subscribe_to_task(connection_id, task_id)
        
        # 发送任务当前状态
        await connection_manager.send_personal_message(connection_id, {
            "type": "task_status",
            "task_id": task_id,
            "data": {
                "status": task.status,
                "progress": task.progress,
                "current_node_index": task.current_node_index,
                "error_message": task.error_message,
                "logs": task.logs or []
            }
        })
        
        # 保持连接
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理任务相关消息
                if message.get("type") == "ping":
                    await connection_manager.send_personal_message(connection_id, {
                        "type": "pong",
                        "task_id": task_id
                    })
                
            except json.JSONDecodeError:
                await connection_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
    
    except WebSocketDisconnect:
        logger.info(
            "Task WebSocket disconnected",
            connection_id=connection_id,
            task_id=task_id,
            user_id=user.id
        )
    except Exception as e:
        logger.error(
            "Task WebSocket error",
            connection_id=connection_id,
            task_id=task_id,
            error=str(e)
        )
    finally:
        # 清理连接
        connection_manager.disconnect(connection_id, user.id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计"""
    return connection_manager.get_connection_stats()
