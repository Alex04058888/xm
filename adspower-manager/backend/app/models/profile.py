"""
浏览器环境配置模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Profile(Base):
    """浏览器环境配置表"""
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 基本信息
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    adspower_id = Column(String(50), unique=True, index=True)
    
    # 配置信息
    fingerprint = Column(JSONB)  # 指纹配置
    proxy_config = Column(JSONB)  # 代理配置
    browser_config = Column(JSONB)  # 浏览器配置
    
    # 状态信息
    status = Column(String(20), default="inactive", nullable=False, index=True)  # inactive, active, running, error
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 标签和分组
    tags = Column(ARRAY(String))
    group_name = Column(String(100))
    
    # 统计信息
    launch_count = Column(Integer, default=0)
    last_launched_at = Column(DateTime(timezone=True))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="profiles")
    tasks = relationship("Task", back_populates="profile", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Profile(id={self.id}, name='{self.name}', status='{self.status}')>"

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == "running"

    @property
    def can_launch(self) -> bool:
        """是否可以启动"""
        return self.is_active and self.status in ["inactive", "active"]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "adspower_id": self.adspower_id,
            "fingerprint": self.fingerprint,
            "proxy_config": self.proxy_config,
            "browser_config": self.browser_config,
            "status": self.status,
            "is_active": self.is_active,
            "tags": self.tags,
            "group_name": self.group_name,
            "launch_count": self.launch_count,
            "last_launched_at": self.last_launched_at.isoformat() if self.last_launched_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_status(self, new_status: str):
        """更新状态"""
        self.status = new_status
        if new_status == "running":
            self.launch_count += 1
            self.last_launched_at = func.now()


class ProfileGroup(Base):
    """环境分组表"""
    __tablename__ = "profile_groups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    color = Column(String(7))  # 十六进制颜色代码
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User")

    def __repr__(self):
        return f"<ProfileGroup(id={self.id}, name='{self.name}')>"
