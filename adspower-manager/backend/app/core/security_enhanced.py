"""
增强安全模块
"""
import hashlib
import secrets
import hmac
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network
import re
import structlog
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cache import cache
from app.models.user import User

logger = structlog.get_logger()


class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        self.failed_login_attempts = {}
        self.blocked_ips = set()
        self.suspicious_activities = {}
        
        # 安全配置
        self.max_login_attempts = 5
        self.lockout_duration = 900  # 15分钟
        self.rate_limit_window = 60  # 1分钟
        self.max_requests_per_window = 100
        
        # 允许的IP网段（可配置）
        self.allowed_networks = [
            ip_network("10.0.0.0/8"),
            ip_network("172.16.0.0/12"),
            ip_network("192.168.0.0/16"),
            ip_network("127.0.0.0/8"),
        ]
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """验证密码强度"""
        issues = []
        score = 0
        
        # 长度检查
        if len(password) < 8:
            issues.append("密码长度至少8位")
        elif len(password) >= 12:
            score += 2
        else:
            score += 1
        
        # 复杂度检查
        if not re.search(r'[a-z]', password):
            issues.append("密码必须包含小写字母")
        else:
            score += 1
            
        if not re.search(r'[A-Z]', password):
            issues.append("密码必须包含大写字母")
        else:
            score += 1
            
        if not re.search(r'\d', password):
            issues.append("密码必须包含数字")
        else:
            score += 1
            
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("密码必须包含特殊字符")
        else:
            score += 1
        
        # 常见密码检查
        common_passwords = [
            "password", "123456", "admin", "root", "user",
            "qwerty", "abc123", "password123"
        ]
        if password.lower() in common_passwords:
            issues.append("不能使用常见密码")
            score = 0
        
        # 评级
        if score >= 5:
            strength = "强"
        elif score >= 3:
            strength = "中等"
        else:
            strength = "弱"
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "strength": strength,
            "score": score
        }
    
    def check_login_attempts(self, identifier: str) -> bool:
        """检查登录尝试次数"""
        current_time = time.time()
        
        if identifier in self.failed_login_attempts:
            attempts = self.failed_login_attempts[identifier]
            
            # 清理过期的尝试记录
            attempts = [t for t in attempts if current_time - t < self.lockout_duration]
            self.failed_login_attempts[identifier] = attempts
            
            # 检查是否超过最大尝试次数
            if len(attempts) >= self.max_login_attempts:
                logger.warning(
                    "Login attempts exceeded",
                    identifier=identifier,
                    attempts=len(attempts)
                )
                return False
        
        return True
    
    def record_failed_login(self, identifier: str):
        """记录失败的登录尝试"""
        current_time = time.time()
        
        if identifier not in self.failed_login_attempts:
            self.failed_login_attempts[identifier] = []
        
        self.failed_login_attempts[identifier].append(current_time)
        
        logger.warning(
            "Failed login attempt recorded",
            identifier=identifier,
            total_attempts=len(self.failed_login_attempts[identifier])
        )
    
    def clear_login_attempts(self, identifier: str):
        """清除登录尝试记录"""
        if identifier in self.failed_login_attempts:
            del self.failed_login_attempts[identifier]
    
    def check_rate_limit(self, identifier: str, action: str) -> bool:
        """检查速率限制"""
        cache_key = f"rate_limit:{identifier}:{action}"
        current_time = int(time.time())
        window_start = current_time - self.rate_limit_window
        
        # 获取当前窗口的请求记录
        requests = cache.get(cache_key) or []
        
        # 清理过期请求
        requests = [t for t in requests if t > window_start]
        
        # 检查是否超过限制
        if len(requests) >= self.max_requests_per_window:
            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                action=action,
                requests=len(requests)
            )
            return False
        
        # 记录当前请求
        requests.append(current_time)
        cache.set(cache_key, requests, self.rate_limit_window)
        
        return True
    
    def validate_ip_address(self, ip: str) -> bool:
        """验证IP地址是否允许访问"""
        try:
            client_ip = ip_address(ip)
            
            # 检查是否在黑名单中
            if ip in self.blocked_ips:
                logger.warning("Blocked IP attempted access", ip=ip)
                return False
            
            # 检查是否在允许的网段中（如果配置了）
            if self.allowed_networks:
                for network in self.allowed_networks:
                    if client_ip in network:
                        return True
                
                logger.warning("IP not in allowed networks", ip=ip)
                return False
            
            return True
            
        except ValueError:
            logger.error("Invalid IP address", ip=ip)
            return False
    
    def detect_suspicious_activity(self, user_id: int, activity: str, metadata: Dict = None):
        """检测可疑活动"""
        current_time = time.time()
        
        if user_id not in self.suspicious_activities:
            self.suspicious_activities[user_id] = []
        
        # 记录活动
        self.suspicious_activities[user_id].append({
            "activity": activity,
            "timestamp": current_time,
            "metadata": metadata or {}
        })
        
        # 清理旧记录（保留最近1小时）
        hour_ago = current_time - 3600
        self.suspicious_activities[user_id] = [
            a for a in self.suspicious_activities[user_id] 
            if a["timestamp"] > hour_ago
        ]
        
        # 分析可疑模式
        activities = self.suspicious_activities[user_id]
        
        # 检查频繁操作
        if len(activities) > 100:  # 1小时内超过100次操作
            logger.warning(
                "Suspicious high activity detected",
                user_id=user_id,
                activity_count=len(activities)
            )
            return True
        
        # 检查异常时间访问
        night_activities = [
            a for a in activities 
            if datetime.fromtimestamp(a["timestamp"]).hour in [0, 1, 2, 3, 4, 5]
        ]
        if len(night_activities) > 20:
            logger.warning(
                "Suspicious night activity detected",
                user_id=user_id,
                night_activities=len(night_activities)
            )
            return True
        
        return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str, salt: str = None) -> tuple:
        """哈希敏感数据"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行哈希
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            data.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        )
        
        return hashed.hex(), salt
    
    def verify_hash(self, data: str, hashed: str, salt: str) -> bool:
        """验证哈希"""
        new_hash, _ = self.hash_sensitive_data(data, salt)
        return hmac.compare_digest(new_hash, hashed)
    
    def sanitize_input(self, data: Any) -> Any:
        """清理输入数据"""
        if isinstance(data, str):
            # 移除潜在的恶意字符
            data = re.sub(r'[<>"\']', '', data)
            # 限制长度
            if len(data) > 1000:
                data = data[:1000]
        elif isinstance(data, dict):
            return {k: self.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]
        
        return data
    
    def validate_file_upload(self, filename: str, content: bytes) -> Dict[str, Any]:
        """验证文件上传"""
        issues = []
        
        # 文件名检查
        if not filename or len(filename) > 255:
            issues.append("文件名无效")
        
        # 扩展名检查
        allowed_extensions = {'.txt', '.csv', '.xlsx', '.json', '.png', '.jpg', '.jpeg'}
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if file_ext not in allowed_extensions:
            issues.append(f"不支持的文件类型: {file_ext}")
        
        # 文件大小检查
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content) > max_size:
            issues.append("文件大小超过限制")
        
        # 文件内容检查（简单的恶意内容检测）
        if b'<script' in content.lower() or b'javascript:' in content.lower():
            issues.append("文件包含可疑内容")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }


# 全局安全管理器
security_manager = SecurityManager()


def require_secure_headers(func):
    """要求安全头的装饰器"""
    def wrapper(*args, **kwargs):
        # 这里可以添加安全头检查逻辑
        return func(*args, **kwargs)
    return wrapper


def audit_log(action: str, resource: str = None, details: Dict = None):
    """审计日志装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            user_id = None
            
            # 尝试从参数中获取用户信息
            for arg in args:
                if hasattr(arg, 'id') and hasattr(arg, 'username'):
                    user_id = arg.id
                    break
            
            try:
                result = func(*args, **kwargs)
                
                # 记录成功的操作
                logger.info(
                    "Audit log",
                    action=action,
                    resource=resource,
                    user_id=user_id,
                    status="success",
                    duration=time.time() - start_time,
                    details=details
                )
                
                return result
                
            except Exception as e:
                # 记录失败的操作
                logger.error(
                    "Audit log",
                    action=action,
                    resource=resource,
                    user_id=user_id,
                    status="failed",
                    error=str(e),
                    duration=time.time() - start_time,
                    details=details
                )
                raise
        
        return wrapper
    return decorator
