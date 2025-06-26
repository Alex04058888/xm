"""
RPA流程模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RPAFlow(Base):
    """RPA流程表"""
    __tablename__ = "rpa_flows"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 基本信息
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(50))  # 分类：web_automation, data_processing, social_media等
    
    # 流程配置
    nodes = Column(JSONB, nullable=False)  # RPA节点配置
    variables = Column(JSONB, default={})  # 流程变量
    settings = Column(JSONB, default={})  # 流程设置
    
    # 版本控制
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_template = Column(Boolean, default=False, nullable=False)
    
    # 统计信息
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime(timezone=True))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="rpa_flows")
    tasks = relationship("Task", back_populates="rpa_flow", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RPAFlow(id={self.id}, name='{self.name}', version={self.version})>"

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100

    @property
    def node_count(self) -> int:
        """节点数量"""
        if not self.nodes or not isinstance(self.nodes, list):
            return 0
        return len(self.nodes)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "nodes": self.nodes,
            "variables": self.variables,
            "settings": self.settings,
            "version": self.version,
            "is_active": self.is_active,
            "is_template": self.is_template,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "node_count": self.node_count,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def increment_execution(self, success: bool = True):
        """增加执行计数"""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.last_executed_at = func.now()


class RPATemplate(Base):
    """RPA模板表"""
    __tablename__ = "rpa_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(50), nullable=False, index=True)
    
    # 模板配置
    nodes = Column(JSONB, nullable=False)
    variables = Column(JSONB, default={})
    settings = Column(JSONB, default={})
    
    # 模板信息
    author = Column(String(100))
    version = Column(String(20), default="1.0.0")
    is_public = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<RPATemplate(id={self.id}, name='{self.name}', category='{self.category}')>"
