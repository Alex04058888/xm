"""
AdsPower Local API客户端封装
"""
import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class AdsPowerAPIError(Exception):
    """AdsPower API异常"""
    def __init__(self, message: str, code: int = None, details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class AdsPowerClient:
    """AdsPower Local API客户端"""
    
    def __init__(self, base_url: str = None, timeout: int = None):
        self.base_url = base_url or settings.ADSPOWER_API_BASE
        self.timeout = timeout or settings.ADSPOWER_API_TIMEOUT
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict = None, 
        data: Dict = None,
        retries: int = 3
    ) -> Dict:
        """发送HTTP请求"""
        if not self.session:
            raise AdsPowerAPIError("Client session not initialized")
            
        url = urljoin(self.base_url, endpoint)
        
        for attempt in range(retries + 1):
            try:
                logger.info(
                    "AdsPower API request",
                    method=method,
                    url=url,
                    params=params,
                    attempt=attempt + 1
                )
                
                async with self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data if method != "GET" else None
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            result = json.loads(response_text)
                            logger.info(
                                "AdsPower API response",
                                status=response.status,
                                code=result.get("code"),
                                msg=result.get("msg")
                            )
                            return result
                        except json.JSONDecodeError:
                            raise AdsPowerAPIError(f"Invalid JSON response: {response_text}")
                    else:
                        logger.error(
                            "AdsPower API error",
                            status=response.status,
                            response=response_text
                        )
                        raise AdsPowerAPIError(
                            f"HTTP {response.status}: {response_text}",
                            code=response.status
                        )
                        
            except aiohttp.ClientError as e:
                if attempt == retries:
                    raise AdsPowerAPIError(f"Network error: {str(e)}")
                
                # 指数退避重试
                wait_time = 2 ** attempt
                logger.warning(
                    "AdsPower API retry",
                    attempt=attempt + 1,
                    wait_time=wait_time,
                    error=str(e)
                )
                await asyncio.sleep(wait_time)
    
    # ==================== 环境管理API ====================
    
    async def create_profile(
        self,
        name: str,
        group_id: str = None,
        domain_name: str = None,
        open_urls: str = None,
        repeat_config: List[str] = None,
        username: str = None,
        password: str = None,
        fakey: str = None,
        cookie: str = None,
        ignore_cookie_error: int = 1,
        ip: str = None,
        country: str = None,
        region: str = None,
        city: str = None,
        remark: str = None,
        ipchecker: int = 2,
        sys: str = "Windows",
        **kwargs
    ) -> Dict:
        """创建浏览器环境"""
        params = {
            "name": name,
            "group_id": group_id,
            "domain_name": domain_name,
            "open_urls": open_urls,
            "repeat_config": repeat_config,
            "username": username,
            "password": password,
            "fakey": fakey,
            "cookie": cookie,
            "ignore_cookie_error": ignore_cookie_error,
            "ip": ip,
            "country": country,
            "region": region,
            "city": city,
            "remark": remark,
            "ipchecker": ipchecker,
            "sys": sys,
            **kwargs
        }
        
        # 移除None值
        params = {k: v for k, v in params.items() if v is not None}
        
        return await self._request("GET", "/api/v1/user/create", params=params)
    
    async def batch_create_profiles(self, profiles_data: List[Dict]) -> Dict:
        """批量创建环境"""
        if len(profiles_data) > 1000:
            raise AdsPowerAPIError("Batch size cannot exceed 1000")
            
        return await self._request("POST", "/api/v1/user/batchCreate", data=profiles_data)
    
    async def get_profile_list(
        self,
        page: int = 1,
        page_size: int = 50,
        group_id: str = None,
        search: str = None
    ) -> Dict:
        """获取环境列表"""
        params = {
            "page": page,
            "page_size": page_size,
            "group_id": group_id,
            "search": search
        }
        params = {k: v for k, v in params.items() if v is not None}
        
        return await self._request("GET", "/api/v1/user/list", params=params)
    
    async def get_profile_detail(self, user_id: str) -> Dict:
        """获取环境详情"""
        params = {"user_id": user_id}
        return await self._request("GET", "/api/v1/user/detail", params=params)
    
    async def update_profile(self, user_id: str, **kwargs) -> Dict:
        """更新环境配置"""
        params = {"user_id": user_id, **kwargs}
        return await self._request("GET", "/api/v1/user/update", params=params)
    
    async def delete_profile(self, user_ids: List[str]) -> Dict:
        """删除环境"""
        params = {"user_ids": user_ids}
        return await self._request("GET", "/api/v1/user/delete", params=params)
    
    # ==================== 浏览器控制API ====================
    
    async def start_browser(
        self,
        user_id: str,
        ip_tab: int = 0,
        headless: int = 0,
        disable_password_filling: int = 0,
        clear_cache_after_closing: int = 0,
        enable_password_saving: int = 0,
        cdp_mask: int = 0
    ) -> Dict:
        """启动浏览器"""
        params = {
            "user_id": user_id,
            "ip_tab": ip_tab,
            "headless": headless,
            "disable_password_filling": disable_password_filling,
            "clear_cache_after_closing": clear_cache_after_closing,
            "enable_password_saving": enable_password_saving,
            "cdp_mask": cdp_mask
        }
        
        return await self._request("GET", "/api/v1/browser/start", params=params)
    
    async def stop_browser(self, user_id: str) -> Dict:
        """关闭浏览器"""
        params = {"user_id": user_id}
        return await self._request("GET", "/api/v1/browser/stop", params=params)
    
    async def batch_start_browsers(self, user_ids: List[str], threads: int = 5) -> Dict:
        """批量启动浏览器"""
        data = {"user_ids": user_ids, "threads": threads}
        return await self._request("POST", "/api/v1/browser/batchStart", data=data)
    
    async def batch_stop_browsers(self, user_ids: List[str]) -> Dict:
        """批量关闭浏览器"""
        data = {"user_ids": user_ids}
        return await self._request("POST", "/api/v1/browser/batchStop", data=data)
    
    async def get_browser_status(self, user_id: str) -> Dict:
        """获取浏览器状态"""
        params = {"user_id": user_id}
        return await self._request("GET", "/api/v1/browser/status", params=params)
    
    # ==================== 代理管理API ====================
    
    async def check_proxy(self, user_id: str) -> Dict:
        """检测代理"""
        params = {"user_id": user_id}
        return await self._request("GET", "/api/v1/proxy/check", params=params)
    
    async def clone_proxy(self, src_user_id: str, dst_user_ids: List[str]) -> Dict:
        """克隆代理配置"""
        data = {"src_user_id": src_user_id, "dst_user_ids": dst_user_ids}
        return await self._request("POST", "/api/v1/proxy/clone", data=data)
    
    # ==================== 分组管理API ====================
    
    async def get_groups(self) -> Dict:
        """获取分组列表"""
        return await self._request("GET", "/api/v1/group/list")
    
    async def create_group(self, group_name: str, remark: str = None) -> Dict:
        """创建分组"""
        params = {"group_name": group_name, "remark": remark}
        params = {k: v for k, v in params.items() if v is not None}
        return await self._request("GET", "/api/v1/group/create", params=params)
    
    async def move_profiles_to_group(self, group_id: str, user_ids: List[str]) -> Dict:
        """移动环境到分组"""
        data = {"group_id": group_id, "user_ids": user_ids}
        return await self._request("POST", "/api/v1/group/moveProfiles", data=data)
    
    # ==================== 工具方法 ====================
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            result = await self._request("GET", "/api/v1/status")
            return result.get("code") == 0
        except Exception:
            return False
    
    def is_success_response(self, response: Dict) -> bool:
        """检查响应是否成功"""
        return response.get("code") == 0
    
    def get_error_message(self, response: Dict) -> str:
        """获取错误信息"""
        return response.get("msg", "Unknown error")


# 全局客户端实例
adspower_client = AdsPowerClient()
