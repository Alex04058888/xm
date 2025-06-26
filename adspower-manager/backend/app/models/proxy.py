"""
代理配置模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Proxy(Base):
    """代理配置表"""
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # 代理配置
    type = Column(String(20), nullable=False)  # http, https, socks4, socks5
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(100))
    password = Column(String(255))  # 加密存储
    
    # 地理位置信息
    country = Column(String(50))
    region = Column(String(100))
    city = Column(String(100))
    
    # 状态信息
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_check_at = Column(DateTime(timezone=True))
    check_status = Column(String(20))  # success, failed, timeout
    
    # 性能指标
    latency = Column(Integer)  # 延迟（毫秒）
    success_rate = Column(Integer, default=100)  # 成功率（百分比）
    
    # 使用统计
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="proxies")

    def __repr__(self):
        return f"<Proxy(id={self.id}, name='{self.name}', host='{self.host}:{self.port}')>"

    @property
    def is_healthy(self) -> bool:
        """代理是否健康"""
        return (
            self.is_active and 
            self.is_verified and 
            self.success_rate >= 80 and
            (self.latency is None or self.latency < 5000)
        )

    @property
    def connection_string(self) -> str:
        """获取连接字符串"""
        if self.username and self.password:
            return f"{self.type}://{self.username}:{self.password}@{self.host}:{self.port}"
        else:
            return f"{self.type}://{self.host}:{self.port}"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            # 不返回密码
            "country": self.country,
            "region": self.region,
            "city": self.city,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "check_status": self.check_status,
            "latency": self.latency,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_healthy": self.is_healthy,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_check_result(self, success: bool, latency: int = None, error: str = None):
        """更新检测结果"""
        self.last_check_at = func.now()
        self.check_status = "success" if success else "failed"
        
        if success:
            self.is_verified = True
            if latency is not None:
                self.latency = latency
        else:
            self.is_verified = False

    def increment_usage(self):
        """增加使用计数"""
        self.usage_count += 1
        self.last_used_at = func.now()
