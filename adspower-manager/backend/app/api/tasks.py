"""
任务管理API
"""
from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.task import Task
from app.services.task_scheduler import task_scheduler

router = APIRouter()


# Pydantic模型
class TaskCreate(BaseModel):
    profile_id: int = Field(..., gt=0)
    rpa_flow_id: int = Field(..., gt=0)
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    variables: Optional[dict] = Field(default_factory=dict)
    settings: Optional[dict] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = None
    priority: int = Field(5, ge=1, le=10)


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    variables: Optional[dict] = None
    settings: Optional[dict] = None
    priority: Optional[int] = Field(None, ge=1, le=10)


class TaskResponse(BaseModel):
    id: int
    name: Optional[str]
    description: Optional[str]
    status: str
    progress: int
    current_node_index: int
    result: Optional[dict]
    error_message: Optional[str]
    error_node_index: Optional[int]
    variables: dict
    settings: dict
    scheduled_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    duration: Optional[float]
    retry_count: int
    max_retries: int
    priority: int
    created_at: str
    updated_at: Optional[str]
    
    # 关联信息
    profile_name: Optional[str] = None
    rpa_flow_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class TaskLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    node_index: Optional[int]


class TaskExecutionRequest(BaseModel):
    task_ids: List[int] = Field(..., min_items=1, max_items=100)


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    profile_id: Optional[int] = Query(None),
    rpa_flow_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取任务列表"""
    
    query = db.query(Task).filter(Task.user_id == current_user.id)
    
    # 状态过滤
    if status:
        query = query.filter(Task.status == status)
    
    # 环境过滤
    if profile_id:
        query = query.filter(Task.profile_id == profile_id)
    
    # RPA流程过滤
    if rpa_flow_id:
        query = query.filter(Task.rpa_flow_id == rpa_flow_id)
    
    # 按创建时间倒序
    query = query.order_by(Task.created_at.desc())
    
    tasks = query.offset(skip).limit(limit).all()
    
    # 添加关联信息
    result = []
    for task in tasks:
        task_dict = task.to_dict()
        task_dict["profile_name"] = task.profile.name if task.profile else None
        task_dict["rpa_flow_name"] = task.rpa_flow.name if task.rpa_flow else None
        result.append(TaskResponse(**task_dict))
    
    return result


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """创建任务"""
    
    try:
        task = await task_scheduler.create_task(
            db=db,
            user_id=current_user.id,
            **task_data.dict()
        )
        
        # 添加关联信息
        task_dict = task.to_dict()
        task_dict["profile_name"] = task.profile.name if task.profile else None
        task_dict["rpa_flow_name"] = task.rpa_flow.name if task.rpa_flow else None
        
        return TaskResponse(**task_dict)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取任务详情"""
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # 添加关联信息
    task_dict = task.to_dict()
    task_dict["profile_name"] = task.profile.name if task.profile else None
    task_dict["rpa_flow_name"] = task.rpa_flow.name if task.rpa_flow else None
    
    return TaskResponse(**task_dict)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """更新任务"""
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # 只能更新未开始的任务
    if task.status not in ["pending", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update running or completed task"
        )
    
    # 更新字段
    update_data = task_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    
    # 添加关联信息
    task_dict = task.to_dict()
    task_dict["profile_name"] = task.profile.name if task.profile else None
    task_dict["rpa_flow_name"] = task.rpa_flow.name if task.rpa_flow else None
    
    return TaskResponse(**task_dict)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """删除任务"""
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # 如果任务正在运行，先取消
    if task.status == "running":
        await task_scheduler.cancel_task(task_id)
    
    db.delete(task)
    db.commit()
    
    return {"message": "Task deleted successfully"}


@router.post("/{task_id}/execute")
async def execute_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """执行任务"""
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.status not in ["pending", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task cannot be executed"
        )
    
    success = await task_scheduler.execute_task(task_id)
    
    if success:
        return {"message": "Task execution started"}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot start task execution (max concurrent tasks reached)"
        )


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """取消任务"""
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is not running"
        )
    
    success = await task_scheduler.cancel_task(task_id)
    
    if success:
        return {"message": "Task cancelled successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel task"
        )


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """重试任务"""
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if not task.can_retry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task cannot be retried"
        )
    
    success = await task_scheduler.retry_task(task_id)
    
    if success:
        return {"message": "Task retry started"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry task"
        )


@router.get("/{task_id}/logs", response_model=List[TaskLogEntry])
async def get_task_logs(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取任务日志"""
    
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    logs = task.logs or []
    return [TaskLogEntry(**log) for log in logs]


@router.get("/running/status")
async def get_running_tasks_status(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """获取正在运行的任务状态"""
    
    running_task_ids = task_scheduler.get_running_tasks()
    
    return {
        "running_count": len(running_task_ids),
        "max_concurrent": task_scheduler.max_concurrent_tasks,
        "running_task_ids": running_task_ids
    }
