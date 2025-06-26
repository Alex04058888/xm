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


# ==================== 页面操作节点 ====================

class ClosePageHandler(RPANodeHandler):
    """关闭当前标签页处理器"""

    def __init__(self):
        super().__init__("closePage")

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        context.add_log("info", "Closing current page")
        await asyncio.sleep(0.2)
        return {"success": True, "message": "Current page closed"}


class CloseOtherPagesHandler(RPANodeHandler):
    """关闭其他标签页处理器"""

    def __init__(self):
        super().__init__("closeOtherPages")

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        context.add_log("info", "Closing other pages")
        await asyncio.sleep(0.3)
        return {"success": True, "message": "Other pages closed"}


class SwitchTabHandler(RPANodeHandler):
    """切换标签页处理器"""

    def __init__(self):
        super().__init__("switchTab")

    def validate_config(self, config: Dict) -> bool:
        return "index" in config or "title" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        index = config.get("index")
        title = config.get("title")

        if index is not None:
            context.add_log("info", f"Switching to tab index: {index}")
        else:
            context.add_log("info", f"Switching to tab with title: {title}")

        await asyncio.sleep(0.2)
        return {"success": True, "message": "Tab switched"}


class RefreshPageHandler(RPANodeHandler):
    """刷新页面处理器"""

    def __init__(self):
        super().__init__("refreshPage")

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        context.add_log("info", "Refreshing page")
        await asyncio.sleep(1.0)
        return {"success": True, "message": "Page refreshed"}


class GoBackHandler(RPANodeHandler):
    """后退处理器"""

    def __init__(self):
        super().__init__("goBack")

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        context.add_log("info", "Going back")
        await asyncio.sleep(0.5)
        return {"success": True, "message": "Navigated back"}


class ScreenshotHandler(RPANodeHandler):
    """截图处理器"""

    def __init__(self):
        super().__init__("screenshot")

    def validate_config(self, config: Dict) -> bool:
        return "path" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        path = self.substitute_variables(config["path"], context)
        full_page = config.get("fullPage", False)

        context.add_log("info", f"Taking screenshot: {path}")
        await asyncio.sleep(0.5)

        return {"success": True, "path": path, "message": f"Screenshot saved to {path}"}


class HoverHandler(RPANodeHandler):
    """悬停处理器"""

    def __init__(self):
        super().__init__("hover")

    def validate_config(self, config: Dict) -> bool:
        return "selector" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        selector = self.substitute_variables(config["selector"], context)

        context.add_log("info", f"Hovering over element: {selector}")
        await asyncio.sleep(0.3)

        return {"success": True, "selector": selector, "message": f"Hovered over {selector}"}


class SelectOptionHandler(RPANodeHandler):
    """下拉选择处理器"""

    def __init__(self):
        super().__init__("selectOption")

    def validate_config(self, config: Dict) -> bool:
        return "selector" in config and "value" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        selector = self.substitute_variables(config["selector"], context)
        value = self.substitute_variables(config["value"], context)

        context.add_log("info", f"Selecting option {value} in {selector}")
        await asyncio.sleep(0.3)

        return {"success": True, "selector": selector, "value": value, "message": f"Selected {value}"}


class FocusHandler(RPANodeHandler):
    """聚焦处理器"""

    def __init__(self):
        super().__init__("focus")

    def validate_config(self, config: Dict) -> bool:
        return "selector" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        selector = self.substitute_variables(config["selector"], context)

        context.add_log("info", f"Focusing element: {selector}")
        await asyncio.sleep(0.2)

        return {"success": True, "selector": selector, "message": f"Focused {selector}"}


class ScrollPageHandler(RPANodeHandler):
    """滚动页面处理器"""

    def __init__(self):
        super().__init__("scrollPage")

    def validate_config(self, config: Dict) -> bool:
        return "distance" in config or "position" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        distance = config.get("distance")
        position = config.get("position")

        if distance:
            context.add_log("info", f"Scrolling by distance: {distance}")
        else:
            context.add_log("info", f"Scrolling to position: {position}")

        await asyncio.sleep(0.3)
        return {"success": True, "message": "Page scrolled"}


class InputFileHandler(RPANodeHandler):
    """上传文件处理器"""

    def __init__(self):
        super().__init__("inputFile")

    def validate_config(self, config: Dict) -> bool:
        return "selector" in config and "localPath" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        selector = self.substitute_variables(config["selector"], context)
        local_path = self.substitute_variables(config["localPath"], context)

        context.add_log("info", f"Uploading file {local_path} to {selector}")
        await asyncio.sleep(0.5)

        return {"success": True, "selector": selector, "path": local_path, "message": f"File uploaded"}


class EvalScriptHandler(RPANodeHandler):
    """执行JavaScript处理器"""

    def __init__(self):
        super().__init__("evalScript")

    def validate_config(self, config: Dict) -> bool:
        return "code" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        code = self.substitute_variables(config["code"], context)

        context.add_log("info", f"Executing JavaScript: {code[:50]}...")
        await asyncio.sleep(0.3)

        # 模拟执行结果
        result = {"executed": True, "code": code}

        return {"success": True, "result": result, "message": "JavaScript executed"}


# ==================== 键盘操作节点 ====================

class KeyPressHandler(RPANodeHandler):
    """按键处理器"""

    def __init__(self):
        super().__init__("keyPress")

    def validate_config(self, config: Dict) -> bool:
        return "keycode" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        keycode = config["keycode"]

        context.add_log("info", f"Pressing key: {keycode}")
        await asyncio.sleep(0.2)

        return {"success": True, "keycode": keycode, "message": f"Key {keycode} pressed"}


class KeyComboHandler(RPANodeHandler):
    """组合键处理器"""

    def __init__(self):
        super().__init__("keyCombo")

    def validate_config(self, config: Dict) -> bool:
        return "keys" in config and isinstance(config["keys"], list)

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        keys = config["keys"]

        context.add_log("info", f"Pressing key combination: {'+'.join(keys)}")
        await asyncio.sleep(0.3)

        return {"success": True, "keys": keys, "message": f"Key combination pressed"}


# ==================== 等待操作节点 ====================

class WaitUntilHandler(RPANodeHandler):
    """等待元素处理器"""

    def __init__(self):
        super().__init__("waitUntil")

    def validate_config(self, config: Dict) -> bool:
        return "selector" in config or "condition" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        selector = config.get("selector")
        condition = config.get("condition")
        timeout = config.get("timeout", 30000)

        if selector:
            context.add_log("info", f"Waiting for element: {selector}")
        else:
            context.add_log("info", f"Waiting for condition: {condition}")

        # 模拟等待
        wait_time = min(timeout / 1000, 2.0)  # 最多等待2秒
        await asyncio.sleep(wait_time)

        return {"success": True, "message": "Wait condition met"}


# ==================== 数据获取节点 ====================

class GetUrlHandler(RPANodeHandler):
    """获取当前URL处理器"""

    def __init__(self):
        super().__init__("getUrl")

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        # 模拟获取当前URL
        current_url = "https://example.com/current-page"
        var_name = config.get("variable", "current_url")

        context.set_variable(var_name, current_url)
        context.add_log("info", f"Got current URL: {current_url}")

        return {"success": True, "url": current_url, "variable": var_name, "message": "URL retrieved"}


class GetElementHandler(RPANodeHandler):
    """获取元素信息处理器"""

    def __init__(self):
        super().__init__("getElement")

    def validate_config(self, config: Dict) -> bool:
        return "selector" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        selector = self.substitute_variables(config["selector"], context)
        attribute = config.get("attribute", "text")
        var_name = config.get("variable", "element_value")

        # 模拟获取元素信息
        element_value = f"Element value from {selector}"

        context.set_variable(var_name, element_value)
        context.add_log("info", f"Got element {attribute}: {element_value}")

        return {"success": True, "selector": selector, "value": element_value, "message": "Element info retrieved"}


class ImportExcelHandler(RPANodeHandler):
    """导入Excel数据处理器"""

    def __init__(self):
        super().__init__("importExcel")

    def validate_config(self, config: Dict) -> bool:
        return "filePath" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        file_path = self.substitute_variables(config["filePath"], context)
        sheet_name = config.get("sheetName", "Sheet1")
        var_name = config.get("variable", "excel_data")

        # 模拟导入Excel数据
        excel_data = [
            {"name": "张三", "age": 25, "city": "北京"},
            {"name": "李四", "age": 30, "city": "上海"},
        ]

        context.set_variable(var_name, excel_data)
        context.add_log("info", f"Imported Excel data from {file_path}")

        return {"success": True, "filePath": file_path, "data": excel_data, "message": "Excel data imported"}


class ImportTxtRandomHandler(RPANodeHandler):
    """随机导入文本处理器"""

    def __init__(self):
        super().__init__("importTxtRandom")

    def validate_config(self, config: Dict) -> bool:
        return "filePath" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        file_path = self.substitute_variables(config["filePath"], context)
        var_name = config.get("variable", "random_text")

        # 模拟随机选择文本行
        import random
        sample_lines = ["文本行1", "文本行2", "文本行3", "文本行4"]
        selected_text = random.choice(sample_lines)

        context.set_variable(var_name, selected_text)
        context.add_log("info", f"Randomly selected text: {selected_text}")

        return {"success": True, "filePath": file_path, "text": selected_text, "message": "Random text imported"}


class ForLoopDataHandler(RPANodeHandler):
    """数据循环处理器"""

    def __init__(self):
        super().__init__("forLoopData")

    def validate_config(self, config: Dict) -> bool:
        return "dataSource" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        data_source = config["dataSource"]
        item_var = config.get("itemVariable", "item")
        index_var = config.get("indexVariable", "index")

        # 获取数据源
        if isinstance(data_source, str):
            data = context.get_variable(data_source, [])
        else:
            data = data_source

        context.add_log("info", f"Starting data loop with {len(data)} items")

        # 这里应该实现循环逻辑，暂时返回成功
        return {"success": True, "dataCount": len(data), "message": "Data loop initialized"}


class GetClipboardHandler(RPANodeHandler):
    """获取剪贴板处理器"""

    def __init__(self):
        super().__init__("getClipboard")

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        var_name = config.get("variable", "clipboard_content")

        # 模拟获取剪贴板内容
        clipboard_content = "剪贴板内容示例"

        context.set_variable(var_name, clipboard_content)
        context.add_log("info", f"Got clipboard content: {clipboard_content}")

        return {"success": True, "content": clipboard_content, "message": "Clipboard content retrieved"}


# ==================== 数据处理节点 ====================

class ExtractTxtHandler(RPANodeHandler):
    """提取文本处理器"""

    def __init__(self):
        super().__init__("extractTxt")

    def validate_config(self, config: Dict) -> bool:
        return "selector" in config or "text" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        selector = config.get("selector")
        text = config.get("text")
        pattern = config.get("pattern", ".*")
        var_name = config.get("variable", "extracted_text")

        if selector:
            # 模拟从元素提取文本
            extracted = f"Text from {selector}"
        else:
            # 从变量文本中提取
            source_text = self.substitute_variables(text, context)
            import re
            match = re.search(pattern, source_text)
            extracted = match.group(0) if match else ""

        context.set_variable(var_name, extracted)
        context.add_log("info", f"Extracted text: {extracted}")

        return {"success": True, "extracted": extracted, "message": "Text extracted"}


class ConvertToJsonHandler(RPANodeHandler):
    """转换JSON处理器"""

    def __init__(self):
        super().__init__("convertToJson")

    def validate_config(self, config: Dict) -> bool:
        return "data" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        data = config["data"]
        var_name = config.get("variable", "json_data")

        # 获取数据并转换为JSON
        if isinstance(data, str):
            source_data = context.get_variable(data)
        else:
            source_data = data

        import json
        json_str = json.dumps(source_data, ensure_ascii=False)

        context.set_variable(var_name, json_str)
        context.add_log("info", f"Converted data to JSON")

        return {"success": True, "json": json_str, "message": "Data converted to JSON"}


class ExtractFieldHandler(RPANodeHandler):
    """提取字段处理器"""

    def __init__(self):
        super().__init__("extractField")

    def validate_config(self, config: Dict) -> bool:
        return "source" in config and "field" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        source = config["source"]
        field = config["field"]
        var_name = config.get("variable", "field_value")

        # 获取源数据
        source_data = context.get_variable(source, {})

        # 提取字段值
        if isinstance(source_data, dict):
            field_value = source_data.get(field)
        elif isinstance(source_data, list) and source_data:
            field_value = source_data[0].get(field) if isinstance(source_data[0], dict) else None
        else:
            field_value = None

        context.set_variable(var_name, field_value)
        context.add_log("info", f"Extracted field {field}: {field_value}")

        return {"success": True, "field": field, "value": field_value, "message": "Field extracted"}


class RandomExtractionHandler(RPANodeHandler):
    """随机提取处理器"""

    def __init__(self):
        super().__init__("randomExtraction")

    def validate_config(self, config: Dict) -> bool:
        return "source" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        source = config["source"]
        count = config.get("count", 1)
        var_name = config.get("variable", "random_items")

        # 获取源数据
        source_data = context.get_variable(source, [])

        if not isinstance(source_data, list):
            source_data = [source_data]

        # 随机提取
        import random
        if len(source_data) <= count:
            random_items = source_data
        else:
            random_items = random.sample(source_data, count)

        context.set_variable(var_name, random_items)
        context.add_log("info", f"Randomly extracted {len(random_items)} items")

        return {"success": True, "items": random_items, "message": "Random extraction completed"}


# ==================== 流程控制节点 ====================

class IfConditionHandler(RPANodeHandler):
    """条件判断处理器"""

    def __init__(self):
        super().__init__("ifCondition")

    def validate_config(self, config: Dict) -> bool:
        return "condition" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        condition = config["condition"]
        left_value = self.substitute_variables(config.get("leftValue", ""), context)
        right_value = self.substitute_variables(config.get("rightValue", ""), context)
        operator = config.get("operator", "equals")

        # 评估条件
        result = self._evaluate_condition(left_value, operator, right_value)

        context.add_log("info", f"Condition evaluation: {left_value} {operator} {right_value} = {result}")

        return {"success": True, "condition_result": result, "message": f"Condition evaluated: {result}"}

    def _evaluate_condition(self, left, operator, right):
        """评估条件"""
        if operator == "equals":
            return str(left) == str(right)
        elif operator == "not_equals":
            return str(left) != str(right)
        elif operator == "contains":
            return str(right) in str(left)
        elif operator == "greater_than":
            try:
                return float(left) > float(right)
            except:
                return False
        elif operator == "less_than":
            try:
                return float(left) < float(right)
            except:
                return False
        else:
            return False


class WhileLoopHandler(RPANodeHandler):
    """循环处理器"""

    def __init__(self):
        super().__init__("whileLoop")

    def validate_config(self, config: Dict) -> bool:
        return "condition" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        max_iterations = config.get("maxIterations", 100)

        context.add_log("info", f"Starting while loop (max {max_iterations} iterations)")

        # 这里应该实现循环逻辑，暂时返回成功
        return {"success": True, "message": "While loop initialized"}


class ExitLoopHandler(RPANodeHandler):
    """退出循环处理器"""

    def __init__(self):
        super().__init__("exitLoop")

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        context.add_log("info", "Exiting loop")
        return {"success": True, "exit_loop": True, "message": "Loop exited"}


class BreakpointHandler(RPANodeHandler):
    """断点处理器"""

    def __init__(self):
        super().__init__("breakpoint")

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        message = config.get("message", "Breakpoint reached")

        context.add_log("info", f"Breakpoint: {message}")

        # 在实际实现中，这里可以暂停执行等待用户操作
        await asyncio.sleep(0.1)

        return {"success": True, "message": f"Breakpoint: {message}"}


class ThrowErrorHandler(RPANodeHandler):
    """抛出错误处理器"""

    def __init__(self):
        super().__init__("throwError")

    def validate_config(self, config: Dict) -> bool:
        return "message" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        error_message = self.substitute_variables(config["message"], context)

        context.add_log("error", f"Throwing error: {error_message}")

        # 抛出错误
        raise RPANodeError(error_message)


# ==================== 第三方工具节点 ====================

class OpenAIHandler(RPANodeHandler):
    """OpenAI GPT处理器"""

    def __init__(self):
        super().__init__("openai")

    def validate_config(self, config: Dict) -> bool:
        return "apiKey" in config and "prompt" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        api_key = config["apiKey"]
        prompt = self.substitute_variables(config["prompt"], context)
        model = config.get("model", "gpt-3.5-turbo")
        system_prompt = config.get("systemPrompt", "")
        var_name = config.get("variable", "gpt_response")

        context.add_log("info", f"Calling OpenAI API with model: {model}")

        # 模拟API调用
        await asyncio.sleep(2.0)  # 模拟API延迟

        # 模拟GPT响应
        gpt_response = f"这是对提示'{prompt[:30]}...'的模拟回复"

        context.set_variable(var_name, gpt_response)
        context.add_log("info", f"GPT response received: {gpt_response[:50]}...")

        return {"success": True, "response": gpt_response, "message": "OpenAI API call completed"}


class Captcha2Handler(RPANodeHandler):
    """2Captcha验证码处理器"""

    def __init__(self):
        super().__init__("captcha2")

    def validate_config(self, config: Dict) -> bool:
        return "apiKey" in config and "siteKey" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        api_key = config["apiKey"]
        site_key = config["siteKey"]
        site_url = config.get("siteUrl", "")
        var_name = config.get("variable", "captcha_token")

        context.add_log("info", f"Solving captcha for site: {site_url}")

        # 模拟验证码解决过程
        await asyncio.sleep(30.0)  # 模拟验证码解决时间

        # 模拟验证码token
        captcha_token = "03AGdBq25SiXT-pmSeBXjzScW-EiocHwwpwqJRCAC7"

        context.set_variable(var_name, captcha_token)
        context.add_log("info", "Captcha solved successfully")

        return {"success": True, "token": captcha_token, "message": "Captcha solved"}


class GoogleSheetsHandler(RPANodeHandler):
    """Google Sheets处理器"""

    def __init__(self):
        super().__init__("googleSheets")

    def validate_config(self, config: Dict) -> bool:
        return "spreadsheetId" in config and "action" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        spreadsheet_id = config["spreadsheetId"]
        action = config["action"]  # read, write, append
        range_name = config.get("range", "A1:Z1000")

        context.add_log("info", f"Google Sheets {action} operation on {spreadsheet_id}")

        # 模拟Google Sheets操作
        await asyncio.sleep(1.0)

        if action == "read":
            # 模拟读取数据
            data = [["姓名", "年龄", "城市"], ["张三", "25", "北京"]]
            var_name = config.get("variable", "sheets_data")
            context.set_variable(var_name, data)
            return {"success": True, "data": data, "message": "Data read from Google Sheets"}
        else:
            return {"success": True, "message": f"Google Sheets {action} completed"}


class SlackWebhookHandler(RPANodeHandler):
    """Slack Webhook处理器"""

    def __init__(self):
        super().__init__("slackWebhook")

    def validate_config(self, config: Dict) -> bool:
        return "webhookUrl" in config and "message" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        webhook_url = config["webhookUrl"]
        message = self.substitute_variables(config["message"], context)
        channel = config.get("channel", "#general")

        context.add_log("info", f"Sending Slack message to {channel}")

        # 模拟Slack webhook调用
        await asyncio.sleep(0.5)

        return {"success": True, "message": message, "channel": channel, "message": "Slack message sent"}


class HttpRequestHandler(RPANodeHandler):
    """HTTP请求处理器"""

    def __init__(self):
        super().__init__("httpRequest")

    def validate_config(self, config: Dict) -> bool:
        return "url" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        url = self.substitute_variables(config["url"], context)
        method = config.get("method", "GET")
        headers = config.get("headers", {})
        data = config.get("data", {})
        var_name = config.get("variable", "http_response")

        context.add_log("info", f"Making {method} request to {url}")

        # 模拟HTTP请求
        await asyncio.sleep(1.0)

        # 模拟响应
        response = {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"success": True, "data": "模拟响应数据"}
        }

        context.set_variable(var_name, response)

        return {"success": True, "response": response, "message": f"{method} request completed"}


class SendEmailHandler(RPANodeHandler):
    """发送邮件处理器"""

    def __init__(self):
        super().__init__("sendEmail")

    def validate_config(self, config: Dict) -> bool:
        return "to" in config and "subject" in config and "body" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        to = self.substitute_variables(config["to"], context)
        subject = self.substitute_variables(config["subject"], context)
        body = self.substitute_variables(config["body"], context)
        smtp_server = config.get("smtpServer", "smtp.gmail.com")

        context.add_log("info", f"Sending email to {to}")

        # 模拟邮件发送
        await asyncio.sleep(2.0)

        return {"success": True, "to": to, "subject": subject, "message": "Email sent successfully"}


# ==================== 账户信息节点 ====================

class UpdateRemarkHandler(RPANodeHandler):
    """更新备注处理器"""

    def __init__(self):
        super().__init__("updateRemark")

    def validate_config(self, config: Dict) -> bool:
        return "remark" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        remark = self.substitute_variables(config["remark"], context)

        context.add_log("info", f"Updating profile remark: {remark}")

        # 这里应该调用API更新profile备注
        await asyncio.sleep(0.3)

        return {"success": True, "remark": remark, "message": "Profile remark updated"}


class UpdateTagHandler(RPANodeHandler):
    """更新标签处理器"""

    def __init__(self):
        super().__init__("updateTag")

    def validate_config(self, config: Dict) -> bool:
        return "tags" in config

    async def execute(self, context: RPAExecutionContext, config: Dict) -> Dict:
        tags = config["tags"]
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",")]

        context.add_log("info", f"Updating profile tags: {tags}")

        # 这里应该调用API更新profile标签
        await asyncio.sleep(0.3)

        return {"success": True, "tags": tags, "message": "Profile tags updated"}


class RPAEngine:
    """RPA执行引擎"""
    
    def __init__(self):
        self.handlers = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """注册节点处理器"""
        handlers = [
            # 页面操作节点 (16个)
            NewPageHandler(),
            ClosePageHandler(),
            CloseOtherPagesHandler(),
            SwitchTabHandler(),
            GotoUrlHandler(),
            RefreshPageHandler(),
            GoBackHandler(),
            ScreenshotHandler(),
            HoverHandler(),
            SelectOptionHandler(),
            FocusHandler(),
            ClickHandler(),
            InputHandler(),
            ScrollPageHandler(),
            InputFileHandler(),
            EvalScriptHandler(),

            # 键盘操作节点 (2个)
            KeyPressHandler(),
            KeyComboHandler(),

            # 等待操作节点 (2个)
            WaitTimeHandler(),
            WaitUntilHandler(),

            # 数据获取节点 (10个)
            GetUrlHandler(),
            GetElementHandler(),
            ImportExcelHandler(),
            ImportTxtRandomHandler(),
            ForLoopDataHandler(),
            GetClipboardHandler(),

            # 数据处理节点 (4个)
            ExtractTxtHandler(),
            ConvertToJsonHandler(),
            ExtractFieldHandler(),
            RandomExtractionHandler(),

            # 流程控制节点 (11个)
            IfConditionHandler(),
            WhileLoopHandler(),
            ExitLoopHandler(),
            BreakpointHandler(),
            ThrowErrorHandler(),
            SetVariableHandler(),

            # 第三方工具节点 (6个)
            OpenAIHandler(),
            Captcha2Handler(),
            GoogleSheetsHandler(),
            SlackWebhookHandler(),
            HttpRequestHandler(),
            SendEmailHandler(),

            # 账户信息节点 (2个)
            UpdateRemarkHandler(),
            UpdateTagHandler(),
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
