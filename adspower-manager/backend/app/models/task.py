"""
任务执行模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Task(Base):
    """任务执行表"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, index=True)
    rpa_flow_id = Column(Integer, ForeignKey("rpa_flows.id"), nullable=False, index=True)
    
    # 任务信息
    name = Column(String(200))  # 任务名称
    description = Column(Text)
    
    # 执行状态
    status = Column(String(20), default="pending", nullable=False, index=True)
    # pending, running, completed, failed, cancelled, paused
    
    progress = Column(Integer, default=0)  # 进度百分比 0-100
    current_node_index = Column(Integer, default=0)  # 当前执行节点索引
    
    # 执行结果
    result = Column(JSONB)  # 执行结果数据
    error_message = Column(Text)  # 错误信息
    error_node_index = Column(Integer)  # 出错节点索引
    
    # 执行日志
    logs = Column(JSONB, default=[])  # 执行日志数组
    
    # 执行配置
    variables = Column(JSONB, default={})  # 任务变量
    settings = Column(JSONB, default={})  # 执行设置
    
    # 时间信息
    scheduled_at = Column(DateTime(timezone=True))  # 计划执行时间
    started_at = Column(DateTime(timezone=True))  # 开始执行时间
    completed_at = Column(DateTime(timezone=True))  # 完成时间
    duration = Column(Float)  # 执行时长（秒）
    
    # 重试信息
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # 优先级
    priority = Column(Integer, default=5)  # 1-10，数字越大优先级越高
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="tasks")
    profile = relationship("Profile", back_populates="tasks")
    rpa_flow = relationship("RPAFlow", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id={self.id}, status='{self.status}', progress={self.progress}%)>"

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == "running"

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status in ["completed", "failed", "cancelled"]

    @property
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.status == "failed" and self.retry_count < self.max_retries

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "profile_id": self.profile_id,
            "rpa_flow_id": self.rpa_flow_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "progress": self.progress,
            "current_node_index": self.current_node_index,
            "result": self.result,
            "error_message": self.error_message,
            "error_node_index": self.error_node_index,
            "logs": self.logs,
            "variables": self.variables,
            "settings": self.settings,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def add_log(self, level: str, message: str, node_index: int = None):
        """添加日志"""
        if not self.logs:
            self.logs = []
        
        log_entry = {
            "timestamp": func.now().isoformat(),
            "level": level,  # info, warning, error, debug
            "message": message,
            "node_index": node_index,
        }
        
        self.logs.append(log_entry)

    def update_progress(self, progress: int, node_index: int = None):
        """更新进度"""
        self.progress = max(0, min(100, progress))
        if node_index is not None:
            self.current_node_index = node_index

    def start_execution(self):
        """开始执行"""
        self.status = "running"
        self.started_at = func.now()
        self.progress = 0

    def complete_execution(self, success: bool = True, result: dict = None, error: str = None):
        """完成执行"""
        self.status = "completed" if success else "failed"
        self.completed_at = func.now()
        self.progress = 100 if success else self.progress
        
        if result:
            self.result = result
        
        if error:
            self.error_message = error
        
        # 计算执行时长
        if self.started_at:
            duration = (func.now() - self.started_at).total_seconds()
            self.duration = duration
