"""
任务调度服务
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import structlog

from app.models.task import Task
from app.models.profile import Profile
from app.models.rpa import RPAFlow
from app.models.user import User
from app.services.rpa_engine import rpa_engine, RPAExecutionContext, RPANodeError
from app.core.database import SessionLocal
from app.services.websocket_manager import task_notifier

logger = structlog.get_logger()


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.running_tasks = {}  # task_id -> asyncio.Task
        self.max_concurrent_tasks = 10
        
    async def create_task(
        self,
        db: Session,
        user_id: int,
        profile_id: int,
        rpa_flow_id: int,
        name: str = None,
        description: str = None,
        variables: Dict = None,
        settings: Dict = None,
        scheduled_at: datetime = None,
        priority: int = 5
    ) -> Task:
        """创建任务"""
        
        # 验证profile和rpa_flow存在
        profile = db.query(Profile).filter(
            and_(Profile.id == profile_id, Profile.user_id == user_id)
        ).first()
        
        if not profile:
            raise ValueError("Profile not found")
        
        rpa_flow = db.query(RPAFlow).filter(
            and_(RPAFlow.id == rpa_flow_id, RPAFlow.user_id == user_id)
        ).first()
        
        if not rpa_flow:
            raise ValueError("RPA flow not found")
        
        if not rpa_flow.is_active:
            raise ValueError("RPA flow is not active")
        
        # 创建任务
        task = Task(
            user_id=user_id,
            profile_id=profile_id,
            rpa_flow_id=rpa_flow_id,
            name=name or f"{rpa_flow.name} - {profile.name}",
            description=description,
            variables=variables or {},
            settings=settings or {},
            scheduled_at=scheduled_at,
            priority=priority,
            status="pending"
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        logger.info(
            "Task created",
            task_id=task.id,
            profile_id=profile_id,
            rpa_flow_id=rpa_flow_id,
            scheduled_at=scheduled_at
        )
        
        # 如果没有设置调度时间，立即执行
        if not scheduled_at:
            await self.execute_task(task.id)
        
        return task
    
    async def execute_task(self, task_id: int) -> bool:
        """执行任务"""
        
        if task_id in self.running_tasks:
            logger.warning("Task already running", task_id=task_id)
            return False
        
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            logger.warning("Max concurrent tasks reached", task_id=task_id)
            return False
        
        # 创建异步任务
        async_task = asyncio.create_task(self._execute_task_async(task_id))
        self.running_tasks[task_id] = async_task
        
        return True
    
    async def _execute_task_async(self, task_id: int):
        """异步执行任务"""
        
        db = SessionLocal()
        
        try:
            # 获取任务信息
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error("Task not found", task_id=task_id)
                return
            
            profile = db.query(Profile).filter(Profile.id == task.profile_id).first()
            rpa_flow = db.query(RPAFlow).filter(RPAFlow.id == task.rpa_flow_id).first()
            
            if not profile or not rpa_flow:
                logger.error("Profile or RPA flow not found", task_id=task_id)
                task.complete_execution(False, error="Profile or RPA flow not found")
                db.commit()
                return
            
            # 检查profile状态
            if not profile.can_launch:
                logger.error("Profile cannot be launched", task_id=task_id, profile_status=profile.status)
                task.complete_execution(False, error=f"Profile cannot be launched: {profile.status}")
                db.commit()
                return
            
            # 开始执行
            task.start_execution()
            db.commit()

            logger.info("Task execution started", task_id=task_id)

            # 通知WebSocket客户端任务开始
            await task_notifier.notify_task_started(task_id, task.to_dict())
            
            # 创建执行上下文
            context = RPAExecutionContext(task, profile, rpa_flow)
            
            # 执行RPA流程
            result = await rpa_engine.execute_flow(context)
            
            # 更新任务结果
            task.complete_execution(True, result=result)
            task.logs = context.execution_logs

            # 更新RPA流程统计
            rpa_flow.increment_execution(True)

            # 更新profile状态
            profile.update_status("inactive")

            db.commit()

            logger.info("Task execution completed successfully", task_id=task_id)

            # 通知WebSocket客户端任务完成
            await task_notifier.notify_task_completed(task_id, result)
            
        except RPANodeError as e:
            # RPA节点执行错误
            task.complete_execution(False, error=e.message)
            task.error_node_index = e.node_index
            
            if hasattr(context, 'execution_logs'):
                task.logs = context.execution_logs
            
            # 更新RPA流程统计
            if 'rpa_flow' in locals():
                rpa_flow.increment_execution(False)
            
            # 更新profile状态
            if 'profile' in locals():
                profile.update_status("inactive")
            
            db.commit()
            
            logger.error(
                "Task execution failed with RPA error",
                task_id=task_id,
                error=e.message,
                node_index=e.node_index,
                node_type=e.node_type
            )

            # 通知WebSocket客户端任务失败
            await task_notifier.notify_task_failed(task_id, e.message, e.node_index)
            
        except Exception as e:
            # 其他错误
            task.complete_execution(False, error=str(e))
            
            if hasattr(context, 'execution_logs'):
                task.logs = context.execution_logs
            
            # 更新RPA流程统计
            if 'rpa_flow' in locals():
                rpa_flow.increment_execution(False)
            
            # 更新profile状态
            if 'profile' in locals():
                profile.update_status("inactive")
            
            db.commit()
            
            logger.error("Task execution failed", task_id=task_id, error=str(e))

            # 通知WebSocket客户端任务失败
            await task_notifier.notify_task_failed(task_id, str(e))
            
        finally:
            # 清理
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            db.close()
    
    async def cancel_task(self, task_id: int) -> bool:
        """取消任务"""
        
        if task_id in self.running_tasks:
            async_task = self.running_tasks[task_id]
            async_task.cancel()
            
            # 更新数据库状态
            db = SessionLocal()
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = "cancelled"
                    task.completed_at = datetime.utcnow()
                    db.commit()
                    
                logger.info("Task cancelled", task_id=task_id)
                return True
                
            finally:
                db.close()
        
        return False
    
    def get_running_tasks(self) -> List[int]:
        """获取正在运行的任务ID列表"""
        return list(self.running_tasks.keys())
    
    def get_task_status(self, task_id: int) -> str:
        """获取任务状态"""
        if task_id in self.running_tasks:
            return "running"
        
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            return task.status if task else "not_found"
        finally:
            db.close()
    
    async def retry_task(self, task_id: int) -> bool:
        """重试任务"""
        
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            
            if not task.can_retry:
                return False
            
            # 重置任务状态
            task.status = "pending"
            task.progress = 0
            task.current_node_index = 0
            task.error_message = None
            task.error_node_index = None
            task.retry_count += 1
            task.started_at = None
            task.completed_at = None
            
            db.commit()
            
            # 重新执行
            return await self.execute_task(task_id)
            
        finally:
            db.close()
    
    async def schedule_periodic_tasks(self):
        """调度定期任务"""
        
        while True:
            try:
                db = SessionLocal()
                
                # 查找需要执行的定时任务
                now = datetime.utcnow()
                pending_tasks = db.query(Task).filter(
                    and_(
                        Task.status == "pending",
                        Task.scheduled_at <= now,
                        Task.scheduled_at.isnot(None)
                    )
                ).limit(10).all()
                
                for task in pending_tasks:
                    if len(self.running_tasks) < self.max_concurrent_tasks:
                        await self.execute_task(task.id)
                    else:
                        break
                
                db.close()
                
            except Exception as e:
                logger.error("Error in periodic task scheduling", error=str(e))
            
            # 每30秒检查一次
            await asyncio.sleep(30)


# 全局任务调度器实例
task_scheduler = TaskScheduler()
