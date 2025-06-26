"""
RPA执行引擎
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

from app.services.adspower_client import adspower_client
from app.models.task import Task
from app.models.profile import Profile
from app.models.rpa import RPAFlow

logger = structlog.get_logger()


class RPANodeError(Exception):
    """RPA节点执行异常"""
    def __init__(self, message: str, node_index: int = None, node_type: str = None):
        self.message = message
        self.node_index = node_index
        self.node_type = node_type
        super().__init__(self.message)


class RPAExecutionContext:
    """RPA执行上下文"""
    
    def __init__(self, task: Task, profile: Profile, rpa_flow: RPAFlow):
        self.task = task
        self.profile = profile
        self.rpa_flow = rpa_flow
        self.variables = task.variables.copy() if task.variables else {}
        self.browser_data = None
        self.current_node_index = 0
        self.execution_logs = []
        
    def set_variable(self, name: str, value: Any):
        """设置变量"""
        self.variables[name] = value
        
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)
        
    def add_log(self, level: str, message: str, node_index: int = None):
        """添加日志"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "node_index": node_index or self.current_node_index
        }
        self.execution_logs.append(log_entry)
        
        logger.info(
            "RPA execution log",
            task_id=self.task.id,
            level=level,
            message=message,
            node_index=node_index
        )


class RPANodeHandler:
    """RPA节点处理器基类"""
    
    def __init__(self, node_type: str):
        self.node_type = node_type
    
    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        """执行节点"""
        raise NotImplementedError
    
    def validate_config(self, config: Dict) -> bool:
        """验证配置"""
        return True
    
    def substitute_variables(self, text: str, context: RPAExecutionContext) -> str:
        """替换变量占位符"""
        if not isinstance(text, str):
            return text
            
        # 简单的变量替换 ${variable_name}
        import re
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            return str(context.get_variable(var_name, match.group(0)))
        
        return re.sub(pattern, replace_var, text)


class NewPageHandler(RPANodeHandler):
    """新建标签页处理器"""
    
    def __init__(self):
        super().__init__("newPage")
    
    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        """执行新建标签页"""
        context.add_log("info", "Creating new page")
        
        # 这里应该调用浏览器API创建新标签页
        # 由于AdsPower API限制，这里只是模拟
        
        return {"success": True, "message": "New page created"}


class GotoUrlHandler(RPANodeHandler):
    """访问网址处理器"""
    
    def __init__(self):
        super().__init__("gotoUrl")
    
    def validate_config(self, config: Dict) -> bool:
        return "url" in config
    
    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        """执行访问网址"""
        url = self.substitute_variables(config["url"], context)
        timeout = config.get("timeout", 30000)
        
        context.add_log("info", f"Navigating to URL: {url}")
        
        # 这里应该调用浏览器API访问URL
        # 由于AdsPower API限制，这里只是模拟
        
        await asyncio.sleep(1)  # 模拟网页加载时间
        
        return {"success": True, "url": url, "message": f"Navigated to {url}"}


class ClickHandler(RPANodeHandler):
    """点击处理器"""
    
    def __init__(self):
        super().__init__("click")
    
    def validate_config(self, config: Dict) -> bool:
        return "selector" in config
    
    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        """执行点击"""
        selector = self.substitute_variables(config["selector"], context)
        serial = config.get("serial", False)
        
        context.add_log("info", f"Clicking element: {selector}")
        
        # 这里应该调用浏览器API点击元素
        # 由于AdsPower API限制，这里只是模拟
        
        await asyncio.sleep(0.5)  # 模拟点击延迟
        
        return {"success": True, "selector": selector, "message": f"Clicked {selector}"}


class InputHandler(RPANodeHandler):
    """输入处理器"""
    
    def __init__(self):
        super().__init__("input")
    
    def validate_config(self, config: Dict) -> bool:
        return "selector" in config and "text" in config
    
    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        """执行输入"""
        selector = self.substitute_variables(config["selector"], context)
        text = self.substitute_variables(config["text"], context)
        
        context.add_log("info", f"Inputting text to {selector}: {text[:50]}...")
        
        # 这里应该调用浏览器API输入文本
        # 由于AdsPower API限制，这里只是模拟
        
        await asyncio.sleep(0.3)  # 模拟输入延迟
        
        return {"success": True, "selector": selector, "text": text, "message": f"Input text to {selector}"}


class WaitTimeHandler(RPANodeHandler):
    """等待时间处理器"""
    
    def __init__(self):
        super().__init__("waitTime")
    
    def validate_config(self, config: Dict) -> bool:
        return "timeout" in config or "timeoutType" in config
    
    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        """执行等待"""
        timeout_type = config.get("timeoutType", "fixed")
        
        if timeout_type == "fixed":
            timeout = config.get("timeout", 1000)
        elif timeout_type == "randomInterval":
            import random
            timeout_min = config.get("timeoutMin", 1000)
            timeout_max = config.get("timeoutMax", 3000)
            timeout = random.randint(timeout_min, timeout_max)
        else:
            timeout = config.get("timeout", 1000)
        
        wait_seconds = timeout / 1000
        context.add_log("info", f"Waiting for {wait_seconds} seconds")
        
        await asyncio.sleep(wait_seconds)
        
        return {"success": True, "timeout": timeout, "message": f"Waited {wait_seconds} seconds"}


class SetVariableHandler(RPANodeHandler):
    """设置变量处理器"""
    
    def __init__(self):
        super().__init__("setVariable")
    
    def validate_config(self, config: Dict) -> bool:
        return "name" in config and "value" in config
    
    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        """执行设置变量"""
        name = config["name"]
        value = self.substitute_variables(config["value"], context)
        
        context.set_variable(name, value)
        context.add_log("info", f"Set variable {name} = {value}")
        
        return {"success": True, "name": name, "value": value, "message": f"Variable {name} set"}


class RPAEngine:
    """RPA执行引擎"""
    
    def __init__(self):
        self.handlers = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """注册节点处理器"""
        handlers = [
            NewPageHandler(),
            GotoUrlHandler(),
            ClickHandler(),
            InputHandler(),
            WaitTimeHandler(),
            SetVariableHandler(),
        ]
        
        for handler in handlers:
            self.handlers[handler.node_type] = handler
    
    def register_handler(self, handler: RPANodeHandler):
        """注册自定义处理器"""
        self.handlers[handler.node_type] = handler
    
    async def execute_flow(self, context: RPAExecutionContext) -> Dict:
        """执行RPA流程"""
        
        try:
            context.add_log("info", "Starting RPA flow execution")
            
            # 启动浏览器
            browser_data = await self._start_browser(context)
            context.browser_data = browser_data
            
            # 执行节点
            nodes = context.rpa_flow.nodes
            if not isinstance(nodes, list):
                raise RPANodeError("Invalid nodes format")
            
            total_nodes = len(nodes)
            
            for i, node in enumerate(nodes):
                context.current_node_index = i
                
                # 更新进度
                progress = int((i / total_nodes) * 100)
                context.task.update_progress(progress, i)
                
                # 执行节点
                result = await self._execute_node(context, node, i)
                
                if not result.get("success", False):
                    raise RPANodeError(
                        result.get("message", "Node execution failed"),
                        node_index=i,
                        node_type=node.get("type")
                    )
                
                context.add_log("info", f"Node {i} completed: {node.get('type')}")
            
            # 完成执行
            context.task.update_progress(100)
            context.add_log("info", "RPA flow execution completed successfully")
            
            return {
                "success": True,
                "message": "Flow executed successfully",
                "variables": context.variables,
                "logs": context.execution_logs
            }
            
        except Exception as e:
            context.add_log("error", f"Flow execution failed: {str(e)}")
            raise
        
        finally:
            # 清理资源
            await self._cleanup(context)
    
    async def _execute_node(self, context: RPAExecutionContext, node: Dict, index: int) -> Dict:
        """执行单个节点"""
        
        node_type = node.get("type")
        if not node_type:
            raise RPANodeError("Node type not specified", node_index=index)
        
        handler = self.handlers.get(node_type)
        if not handler:
            raise RPANodeError(f"Unknown node type: {node_type}", node_index=index, node_type=node_type)
        
        config = node.get("config", {})
        
        # 验证配置
        if not handler.validate_config(config):
            raise RPANodeError(f"Invalid config for node {node_type}", node_index=index, node_type=node_type)
        
        # 执行节点
        try:
            result = await handler.execute(context, config)
            return result
        except Exception as e:
            raise RPANodeError(f"Node execution error: {str(e)}", node_index=index, node_type=node_type)
    
    async def _start_browser(self, context: RPAExecutionContext) -> Dict:
        """启动浏览器"""
        
        try:
            async with adspower_client as client:
                response = await client.start_browser(context.profile.adspower_id)
                
                if not client.is_success_response(response):
                    raise RPANodeError(f"Failed to start browser: {client.get_error_message(response)}")
                
                browser_data = response["data"]
                context.add_log("info", f"Browser started for profile {context.profile.name}")
                
                return browser_data
                
        except Exception as e:
            raise RPANodeError(f"Browser startup failed: {str(e)}")
    
    async def _cleanup(self, context: RPAExecutionContext):
        """清理资源"""
        
        try:
            if context.browser_data:
                async with adspower_client as client:
                    await client.stop_browser(context.profile.adspower_id)
                    context.add_log("info", "Browser stopped")
        except Exception as e:
            context.add_log("warning", f"Failed to stop browser: {str(e)}")


# 全局RPA引擎实例
rpa_engine = RPAEngine()
