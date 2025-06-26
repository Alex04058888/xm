"""
性能监控和优化模块
"""
import time
import psutil
import asyncio
from typing import Dict, Any, Optional
from functools import wraps
from contextlib import asynccontextmanager
import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest

from app.core.config import settings

logger = structlog.get_logger()

# Prometheus指标
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

TASK_EXECUTION_DURATION = Histogram(
    'task_execution_duration_seconds',
    'Task execution duration',
    ['status']
)

ACTIVE_CONNECTIONS = Gauge(
    'websocket_active_connections',
    'Active WebSocket connections'
)

SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage'
)

DATABASE_CONNECTIONS = Gauge(
    'database_active_connections',
    'Active database connections'
)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_stats = {}
        self.task_stats = {}
        
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """记录请求指标"""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        
        # 内存统计
        key = f"{method}:{endpoint}"
        if key not in self.request_stats:
            self.request_stats[key] = {
                'count': 0,
                'total_duration': 0,
                'min_duration': float('inf'),
                'max_duration': 0,
                'error_count': 0
            }
        
        stats = self.request_stats[key]
        stats['count'] += 1
        stats['total_duration'] += duration
        stats['min_duration'] = min(stats['min_duration'], duration)
        stats['max_duration'] = max(stats['max_duration'], duration)
        
        if status_code >= 400:
            stats['error_count'] += 1
    
    def record_task_execution(self, task_id: int, status: str, duration: float):
        """记录任务执行指标"""
        TASK_EXECUTION_DURATION.labels(status=status).observe(duration)
        
        if task_id not in self.task_stats:
            self.task_stats[task_id] = []
        
        self.task_stats[task_id].append({
            'status': status,
            'duration': duration,
            'timestamp': time.time()
        })
    
    def update_system_metrics(self):
        """更新系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            SYSTEM_CPU_USAGE.set(cpu_percent)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            SYSTEM_MEMORY_USAGE.set(memory.percent)
            
            logger.debug(
                "System metrics updated",
                cpu_percent=cpu_percent,
                memory_percent=memory.percent
            )
        except Exception as e:
            logger.error("Failed to update system metrics", error=str(e))
    
    def get_request_stats(self) -> Dict[str, Any]:
        """获取请求统计"""
        stats = {}
        for endpoint, data in self.request_stats.items():
            if data['count'] > 0:
                stats[endpoint] = {
                    'count': data['count'],
                    'avg_duration': data['total_duration'] / data['count'],
                    'min_duration': data['min_duration'],
                    'max_duration': data['max_duration'],
                    'error_rate': data['error_count'] / data['count'] * 100
                }
        return stats
    
    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计"""
        total_tasks = len(self.task_stats)
        if total_tasks == 0:
            return {}
        
        all_executions = []
        for executions in self.task_stats.values():
            all_executions.extend(executions)
        
        if not all_executions:
            return {}
        
        success_count = sum(1 for e in all_executions if e['status'] == 'completed')
        failed_count = sum(1 for e in all_executions if e['status'] == 'failed')
        total_duration = sum(e['duration'] for e in all_executions)
        
        return {
            'total_tasks': total_tasks,
            'total_executions': len(all_executions),
            'success_rate': success_count / len(all_executions) * 100,
            'failure_rate': failed_count / len(all_executions) * 100,
            'avg_duration': total_duration / len(all_executions),
            'uptime': time.time() - self.start_time
        }
    
    def get_prometheus_metrics(self) -> str:
        """获取Prometheus格式的指标"""
        return generate_latest()


# 全局性能监控器
performance_monitor = PerformanceMonitor()


def monitor_performance(func_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        name = func_name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.debug(
                        "Function executed",
                        function=name,
                        duration=duration,
                        status="success"
                    )
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(
                        "Function failed",
                        function=name,
                        duration=duration,
                        error=str(e),
                        status="error"
                    )
                    raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.debug(
                        "Function executed",
                        function=name,
                        duration=duration,
                        status="success"
                    )
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(
                        "Function failed",
                        function=name,
                        duration=duration,
                        error=str(e),
                        status="error"
                    )
                    raise
            return sync_wrapper
    return decorator


@asynccontextmanager
async def performance_context(operation_name: str):
    """性能监控上下文管理器"""
    start_time = time.time()
    try:
        logger.info("Operation started", operation=operation_name)
        yield
        duration = time.time() - start_time
        logger.info(
            "Operation completed",
            operation=operation_name,
            duration=duration
        )
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "Operation failed",
            operation=operation_name,
            duration=duration,
            error=str(e)
        )
        raise


class DatabasePerformanceMonitor:
    """数据库性能监控"""
    
    def __init__(self):
        self.query_stats = {}
        self.slow_query_threshold = 1.0  # 1秒
    
    def record_query(self, query: str, duration: float, params: tuple = None):
        """记录查询性能"""
        # 简化查询语句用于统计
        query_type = query.strip().split()[0].upper()
        
        if query_type not in self.query_stats:
            self.query_stats[query_type] = {
                'count': 0,
                'total_duration': 0,
                'slow_queries': 0
            }
        
        stats = self.query_stats[query_type]
        stats['count'] += 1
        stats['total_duration'] += duration
        
        if duration > self.slow_query_threshold:
            stats['slow_queries'] += 1
            logger.warning(
                "Slow query detected",
                query_type=query_type,
                duration=duration,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计"""
        stats = {}
        for query_type, data in self.query_stats.items():
            if data['count'] > 0:
                stats[query_type] = {
                    'count': data['count'],
                    'avg_duration': data['total_duration'] / data['count'],
                    'slow_query_rate': data['slow_queries'] / data['count'] * 100
                }
        return stats


# 全局数据库性能监控器
db_performance_monitor = DatabasePerformanceMonitor()


async def start_performance_monitoring():
    """启动性能监控"""
    while True:
        try:
            performance_monitor.update_system_metrics()
            await asyncio.sleep(30)  # 每30秒更新一次系统指标
        except Exception as e:
            logger.error("Performance monitoring error", error=str(e))
            await asyncio.sleep(60)  # 出错时等待更长时间
