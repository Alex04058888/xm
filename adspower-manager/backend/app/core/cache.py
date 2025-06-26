"""
缓存管理模块
"""
import json
import pickle
from typing import Any, Optional, Union, Dict
from datetime import timedelta
import redis
import structlog
from functools import wraps

from app.core.config import settings

logger = structlog.get_logger()


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=False,  # 保持二进制模式以支持pickle
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
    def _serialize(self, value: Any) -> bytes:
        """序列化数据"""
        try:
            # 尝试JSON序列化（更快）
            return json.dumps(value, ensure_ascii=False).encode('utf-8')
        except (TypeError, ValueError):
            # 回退到pickle序列化
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """反序列化数据"""
        try:
            # 尝试JSON反序列化
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # 回退到pickle反序列化
            return pickle.loads(data)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            data = self.redis_client.get(key)
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """设置缓存值"""
        try:
            data = self._serialize(value)
            if ttl is None:
                return self.redis_client.set(key, data)
            elif isinstance(ttl, timedelta):
                return self.redis_client.setex(key, int(ttl.total_seconds()), data)
            else:
                return self.redis_client.setex(key, ttl, data)
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error("Cache exists error", key=key, error=str(e))
            return False
    
    def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """设置过期时间"""
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            return bool(self.redis_client.expire(key, ttl))
        except Exception as e:
            logger.error("Cache expire error", key=key, error=str(e))
            return False
    
    def get_many(self, keys: list) -> Dict[str, Any]:
        """批量获取缓存"""
        try:
            values = self.redis_client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)
            return result
        except Exception as e:
            logger.error("Cache get_many error", keys=keys, error=str(e))
            return {}
    
    def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存"""
        try:
            pipe = self.redis_client.pipeline()
            for key, value in mapping.items():
                data = self._serialize(value)
                if ttl:
                    pipe.setex(key, ttl, data)
                else:
                    pipe.set(key, data)
            pipe.execute()
            return True
        except Exception as e:
            logger.error("Cache set_many error", error=str(e))
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error("Cache clear_pattern error", pattern=pattern, error=str(e))
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            info = self.redis_client.info()
            return {
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "hit_rate": info.get("keyspace_hits", 0) / max(
                    info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1
                ) * 100
            }
        except Exception as e:
            logger.error("Cache stats error", error=str(e))
            return {}


# 全局缓存管理器实例
cache = CacheManager()


def cached(
    key_prefix: str = "",
    ttl: Union[int, timedelta] = 3600,
    key_func: Optional[callable] = None
):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认键生成策略
                func_name = f"{func.__module__}.{func.__name__}"
                args_str = "_".join(str(arg) for arg in args)
                kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{key_prefix}:{func_name}:{args_str}:{kwargs_str}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit", key=cache_key)
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug("Cache miss, stored result", key=cache_key)
            
            return result
        return wrapper
    return decorator


def cache_key_generator(*args, **kwargs) -> str:
    """通用缓存键生成器"""
    parts = []
    for arg in args:
        if hasattr(arg, 'id'):
            parts.append(f"{type(arg).__name__}_{arg.id}")
        else:
            parts.append(str(arg))
    
    for key, value in sorted(kwargs.items()):
        parts.append(f"{key}_{value}")
    
    return ":".join(parts)


# 预定义的缓存键模式
class CacheKeys:
    """缓存键常量"""
    
    # 用户相关
    USER_PROFILE = "user:profile:{user_id}"
    USER_PERMISSIONS = "user:permissions:{user_id}"
    
    # 环境相关
    PROFILE_LIST = "profile:list:{user_id}:{page}:{limit}"
    PROFILE_DETAIL = "profile:detail:{profile_id}"
    PROFILE_STATUS = "profile:status:{profile_id}"
    
    # RPA相关
    RPA_FLOW_LIST = "rpa:flow:list:{user_id}:{page}:{limit}"
    RPA_FLOW_DETAIL = "rpa:flow:detail:{flow_id}"
    RPA_NODE_TEMPLATES = "rpa:node:templates"
    
    # 任务相关
    TASK_LIST = "task:list:{user_id}:{page}:{limit}"
    TASK_DETAIL = "task:detail:{task_id}"
    TASK_LOGS = "task:logs:{task_id}"
    
    # 系统相关
    SYSTEM_STATS = "system:stats"
    API_RATE_LIMIT = "api:rate_limit:{user_id}:{endpoint}"
