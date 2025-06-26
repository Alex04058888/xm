"""
监控告警系统
"""
import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import structlog
from dataclasses import dataclass

from app.core.config import settings
from app.core.cache import cache
from app.services.websocket_manager import connection_manager

logger = structlog.get_logger()


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警信息"""
    id: str
    level: AlertLevel
    title: str
    message: str
    source: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MetricCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics = {}
        self.last_collection = time.time()
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存指标
            memory = psutil.virtual_memory()
            
            # 磁盘指标
            disk = psutil.disk_usage('/')
            
            # 网络指标
            network = psutil.net_io_counters()
            
            # 进程指标
            process = psutil.Process()
            process_memory = process.memory_info()
            
            metrics = {
                "timestamp": time.time(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count,
                    "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "usage_percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "usage_percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": process.cpu_percent()
                }
            }
            
            self.metrics["system"] = metrics
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))
            return {}
    
    async def collect_application_metrics(self) -> Dict[str, Any]:
        """收集应用指标"""
        try:
            from app.services.task_scheduler import task_scheduler
            from app.services.websocket_manager import connection_manager
            
            # 任务指标
            running_tasks = len(task_scheduler.get_running_tasks())
            
            # WebSocket连接指标
            ws_stats = connection_manager.get_connection_stats()
            
            # 缓存指标
            cache_stats = cache.get_stats()
            
            metrics = {
                "timestamp": time.time(),
                "tasks": {
                    "running_count": running_tasks,
                    "max_concurrent": task_scheduler.max_concurrent_tasks
                },
                "websocket": ws_stats,
                "cache": cache_stats
            }
            
            self.metrics["application"] = metrics
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect application metrics", error=str(e))
            return {}
    
    async def collect_database_metrics(self) -> Dict[str, Any]:
        """收集数据库指标"""
        try:
            from app.core.database import engine
            
            # 数据库连接池信息
            pool = engine.pool
            
            metrics = {
                "timestamp": time.time(),
                "connections": {
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
            }
            
            self.metrics["database"] = metrics
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect database metrics", error=str(e))
            return {}


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules: List[Dict] = []
        self.notification_handlers: List[Callable] = []
        self.alert_history: List[Alert] = []
        
        # 默认告警规则
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """设置默认告警规则"""
        self.alert_rules = [
            {
                "name": "high_cpu_usage",
                "condition": lambda metrics: metrics.get("system", {}).get("cpu", {}).get("usage_percent", 0) > 80,
                "level": AlertLevel.WARNING,
                "title": "CPU使用率过高",
                "message": "CPU使用率超过80%",
                "cooldown": 300  # 5分钟冷却期
            },
            {
                "name": "high_memory_usage",
                "condition": lambda metrics: metrics.get("system", {}).get("memory", {}).get("usage_percent", 0) > 85,
                "level": AlertLevel.WARNING,
                "title": "内存使用率过高",
                "message": "内存使用率超过85%",
                "cooldown": 300
            },
            {
                "name": "disk_space_low",
                "condition": lambda metrics: metrics.get("system", {}).get("disk", {}).get("usage_percent", 0) > 90,
                "level": AlertLevel.ERROR,
                "title": "磁盘空间不足",
                "message": "磁盘使用率超过90%",
                "cooldown": 600  # 10分钟冷却期
            },
            {
                "name": "too_many_running_tasks",
                "condition": lambda metrics: metrics.get("application", {}).get("tasks", {}).get("running_count", 0) > 50,
                "level": AlertLevel.WARNING,
                "title": "运行任务过多",
                "message": "当前运行任务数量超过50个",
                "cooldown": 180
            },
            {
                "name": "database_connection_high",
                "condition": lambda metrics: metrics.get("database", {}).get("connections", {}).get("checked_out", 0) > 15,
                "level": AlertLevel.WARNING,
                "title": "数据库连接数过高",
                "message": "数据库连接数超过15个",
                "cooldown": 300
            }
        ]
    
    def add_alert_rule(self, rule: Dict):
        """添加告警规则"""
        required_fields = ["name", "condition", "level", "title", "message"]
        if not all(field in rule for field in required_fields):
            raise ValueError("Alert rule missing required fields")
        
        self.alert_rules.append(rule)
    
    def add_notification_handler(self, handler: Callable):
        """添加通知处理器"""
        self.notification_handlers.append(handler)
    
    async def check_alerts(self, metrics: Dict[str, Any]):
        """检查告警条件"""
        current_time = datetime.utcnow()
        
        for rule in self.alert_rules:
            try:
                # 检查冷却期
                cooldown = rule.get("cooldown", 300)
                last_alert_key = f"last_alert:{rule['name']}"
                last_alert_time = cache.get(last_alert_key)
                
                if last_alert_time and (current_time.timestamp() - last_alert_time) < cooldown:
                    continue
                
                # 检查告警条件
                if rule["condition"](metrics):
                    alert = Alert(
                        id=f"{rule['name']}_{int(current_time.timestamp())}",
                        level=rule["level"],
                        title=rule["title"],
                        message=rule["message"],
                        source="system_monitor",
                        timestamp=current_time,
                        metadata={"rule": rule["name"], "metrics": metrics}
                    )
                    
                    await self._trigger_alert(alert)
                    
                    # 设置冷却期
                    cache.set(last_alert_key, current_time.timestamp(), cooldown)
                    
            except Exception as e:
                logger.error(
                    "Error checking alert rule",
                    rule=rule["name"],
                    error=str(e)
                )
    
    async def _trigger_alert(self, alert: Alert):
        """触发告警"""
        self.alerts.append(alert)
        self.alert_history.append(alert)
        
        # 限制内存中的告警数量
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        logger.warning(
            "Alert triggered",
            alert_id=alert.id,
            level=alert.level.value,
            title=alert.title,
            message=alert.message
        )
        
        # 发送通知
        await self._send_notifications(alert)
    
    async def _send_notifications(self, alert: Alert):
        """发送通知"""
        # WebSocket通知
        try:
            await connection_manager.broadcast_to_all({
                "type": "system_alert",
                "data": {
                    "id": alert.id,
                    "level": alert.level.value,
                    "title": alert.title,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat()
                }
            })
        except Exception as e:
            logger.error("Failed to send WebSocket notification", error=str(e))
        
        # 其他通知处理器
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error("Notification handler failed", error=str(e))
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                logger.info("Alert resolved", alert_id=alert_id)
                break
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """获取告警统计"""
        active_alerts = self.get_active_alerts()
        
        stats = {
            "total_alerts": len(self.alert_history),
            "active_alerts": len(active_alerts),
            "alerts_by_level": {},
            "recent_alerts": len([
                a for a in self.alert_history 
                if (datetime.utcnow() - a.timestamp).total_seconds() < 3600
            ])
        }
        
        # 按级别统计
        for level in AlertLevel:
            stats["alerts_by_level"][level.value] = len([
                a for a in active_alerts if a.level == level
            ])
        
        return stats


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.health_checks = {}
        self.last_check_results = {}
    
    def register_health_check(self, name: str, check_func: Callable):
        """注册健康检查"""
        self.health_checks[name] = check_func
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {}
        overall_healthy = True
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                duration = time.time() - start_time
                
                results[name] = {
                    "healthy": result.get("healthy", True),
                    "message": result.get("message", "OK"),
                    "duration": duration,
                    "timestamp": time.time()
                }
                
                if not results[name]["healthy"]:
                    overall_healthy = False
                    
            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "message": f"Health check failed: {str(e)}",
                    "duration": 0,
                    "timestamp": time.time()
                }
                overall_healthy = False
        
        self.last_check_results = results
        
        return {
            "overall_healthy": overall_healthy,
            "checks": results,
            "timestamp": time.time()
        }


# 全局实例
metric_collector = MetricCollector()
alert_manager = AlertManager()
health_checker = HealthChecker()


async def start_monitoring():
    """启动监控系统"""
    logger.info("Starting monitoring system")
    
    # 注册默认健康检查
    health_checker.register_health_check("database", check_database_health)
    health_checker.register_health_check("cache", check_cache_health)
    health_checker.register_health_check("adspower", check_adspower_health)
    
    while True:
        try:
            # 收集指标
            system_metrics = await metric_collector.collect_system_metrics()
            app_metrics = await metric_collector.collect_application_metrics()
            db_metrics = await metric_collector.collect_database_metrics()
            
            all_metrics = {
                "system": system_metrics,
                "application": app_metrics,
                "database": db_metrics
            }
            
            # 检查告警
            await alert_manager.check_alerts(all_metrics)
            
            # 运行健康检查（每5分钟一次）
            if int(time.time()) % 300 == 0:
                await health_checker.run_health_checks()
            
            await asyncio.sleep(60)  # 每分钟收集一次指标
            
        except Exception as e:
            logger.error("Monitoring error", error=str(e))
            await asyncio.sleep(60)


async def check_database_health() -> Dict[str, Any]:
    """数据库健康检查"""
    try:
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        return {"healthy": True, "message": "Database connection OK"}
    except Exception as e:
        return {"healthy": False, "message": f"Database error: {str(e)}"}


async def check_cache_health() -> Dict[str, Any]:
    """缓存健康检查"""
    try:
        test_key = "health_check_test"
        cache.set(test_key, "test_value", 10)
        value = cache.get(test_key)
        cache.delete(test_key)
        
        if value == "test_value":
            return {"healthy": True, "message": "Cache OK"}
        else:
            return {"healthy": False, "message": "Cache read/write failed"}
    except Exception as e:
        return {"healthy": False, "message": f"Cache error: {str(e)}"}


async def check_adspower_health() -> Dict[str, Any]:
    """AdsPower健康检查"""
    try:
        from app.services.adspower_client import adspower_client
        
        async with adspower_client as client:
            healthy = await client.health_check()
            
        if healthy:
            return {"healthy": True, "message": "AdsPower API OK"}
        else:
            return {"healthy": False, "message": "AdsPower API not responding"}
    except Exception as e:
        return {"healthy": False, "message": f"AdsPower error: {str(e)}"}
