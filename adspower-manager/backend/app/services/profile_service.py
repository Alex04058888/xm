"""
环境管理服务层
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import structlog

from app.models.profile import Profile
from app.models.user import User
from app.services.adspower_client import adspower_client, AdsPowerAPIError
from app.core.config import settings

logger = structlog.get_logger()


class ProfileService:
    """环境管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_profile(
        self,
        user_id: int,
        name: str,
        description: str = None,
        fingerprint: Dict = None,
        proxy_config: Dict = None,
        browser_config: Dict = None,
        tags: List[str] = None,
        group_name: str = None,
        **adspower_params
    ) -> Profile:
        """创建浏览器环境"""
        
        # 检查名称是否重复
        existing = self.db.query(Profile).filter(
            and_(Profile.user_id == user_id, Profile.name == name)
        ).first()
        
        if existing:
            raise ValueError(f"Profile name '{name}' already exists")
        
        try:
            # 调用AdsPower API创建环境
            async with adspower_client as client:
                adspower_response = await client.create_profile(
                    name=name,
                    remark=description,
                    **adspower_params
                )
                
                if not client.is_success_response(adspower_response):
                    raise AdsPowerAPIError(client.get_error_message(adspower_response))
                
                adspower_id = adspower_response["data"]["user_id"]
                
            # 创建数据库记录
            profile = Profile(
                user_id=user_id,
                name=name,
                description=description,
                adspower_id=adspower_id,
                fingerprint=fingerprint or {},
                proxy_config=proxy_config or {},
                browser_config=browser_config or {},
                tags=tags or [],
                group_name=group_name,
                status="inactive"
            )
            
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            
            logger.info(
                "Profile created",
                profile_id=profile.id,
                adspower_id=adspower_id,
                name=name
            )
            
            return profile
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create profile", error=str(e), name=name)
            raise
    
    async def batch_create_profiles(
        self,
        user_id: int,
        profiles_data: List[Dict]
    ) -> List[Profile]:
        """批量创建环境"""
        
        if len(profiles_data) > 1000:
            raise ValueError("Batch size cannot exceed 1000")
        
        created_profiles = []
        
        try:
            # 准备AdsPower API数据
            adspower_data = []
            for data in profiles_data:
                adspower_item = {
                    "name": data["name"],
                    "remark": data.get("description", ""),
                    **data.get("adspower_params", {})
                }
                adspower_data.append(adspower_item)
            
            # 调用AdsPower批量创建API
            async with adspower_client as client:
                adspower_response = await client.batch_create_profiles(adspower_data)
                
                if not client.is_success_response(adspower_response):
                    raise AdsPowerAPIError(client.get_error_message(adspower_response))
                
                created_data = adspower_response["data"]
            
            # 创建数据库记录
            for i, data in enumerate(profiles_data):
                if i < len(created_data):
                    adspower_id = created_data[i]["user_id"]
                    
                    profile = Profile(
                        user_id=user_id,
                        name=data["name"],
                        description=data.get("description"),
                        adspower_id=adspower_id,
                        fingerprint=data.get("fingerprint", {}),
                        proxy_config=data.get("proxy_config", {}),
                        browser_config=data.get("browser_config", {}),
                        tags=data.get("tags", []),
                        group_name=data.get("group_name"),
                        status="inactive"
                    )
                    
                    self.db.add(profile)
                    created_profiles.append(profile)
            
            self.db.commit()
            
            logger.info(
                "Batch profiles created",
                count=len(created_profiles),
                user_id=user_id
            )
            
            return created_profiles
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to batch create profiles", error=str(e))
            raise
    
    def get_profiles(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search: str = None,
        status: str = None,
        group_name: str = None,
        tags: List[str] = None
    ) -> List[Profile]:
        """获取环境列表"""
        
        query = self.db.query(Profile).filter(Profile.user_id == user_id)
        
        # 搜索过滤
        if search:
            query = query.filter(
                or_(
                    Profile.name.ilike(f"%{search}%"),
                    Profile.description.ilike(f"%{search}%")
                )
            )
        
        # 状态过滤
        if status:
            query = query.filter(Profile.status == status)
        
        # 分组过滤
        if group_name:
            query = query.filter(Profile.group_name == group_name)
        
        # 标签过滤
        if tags:
            for tag in tags:
                query = query.filter(Profile.tags.contains([tag]))
        
        return query.offset(skip).limit(limit).all()
    
    def get_profile_by_id(self, user_id: int, profile_id: int) -> Optional[Profile]:
        """根据ID获取环境"""
        return self.db.query(Profile).filter(
            and_(Profile.id == profile_id, Profile.user_id == user_id)
        ).first()
    
    def get_profile_by_adspower_id(self, adspower_id: str) -> Optional[Profile]:
        """根据AdsPower ID获取环境"""
        return self.db.query(Profile).filter(
            Profile.adspower_id == adspower_id
        ).first()
    
    async def update_profile(
        self,
        user_id: int,
        profile_id: int,
        **update_data
    ) -> Profile:
        """更新环境配置"""
        
        profile = self.get_profile_by_id(user_id, profile_id)
        if not profile:
            raise ValueError("Profile not found")
        
        try:
            # 分离AdsPower参数和本地参数
            adspower_params = update_data.pop("adspower_params", {})
            
            # 如果有AdsPower参数，调用API更新
            if adspower_params:
                async with adspower_client as client:
                    adspower_response = await client.update_profile(
                        user_id=profile.adspower_id,
                        **adspower_params
                    )
                    
                    if not client.is_success_response(adspower_response):
                        raise AdsPowerAPIError(client.get_error_message(adspower_response))
            
            # 更新本地数据库
            for key, value in update_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            self.db.commit()
            self.db.refresh(profile)
            
            logger.info(
                "Profile updated",
                profile_id=profile.id,
                adspower_id=profile.adspower_id
            )
            
            return profile
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to update profile", error=str(e), profile_id=profile_id)
            raise
    
    async def delete_profile(self, user_id: int, profile_id: int) -> bool:
        """删除环境"""
        
        profile = self.get_profile_by_id(user_id, profile_id)
        if not profile:
            raise ValueError("Profile not found")
        
        try:
            # 先停止浏览器（如果正在运行）
            if profile.status == "running":
                await self.stop_browser(user_id, profile_id)
            
            # 调用AdsPower API删除
            async with adspower_client as client:
                adspower_response = await client.delete_profile([profile.adspower_id])
                
                if not client.is_success_response(adspower_response):
                    logger.warning(
                        "Failed to delete from AdsPower",
                        error=client.get_error_message(adspower_response),
                        adspower_id=profile.adspower_id
                    )
            
            # 删除数据库记录
            self.db.delete(profile)
            self.db.commit()
            
            logger.info(
                "Profile deleted",
                profile_id=profile.id,
                adspower_id=profile.adspower_id
            )
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to delete profile", error=str(e), profile_id=profile_id)
            raise
    
    async def start_browser(self, user_id: int, profile_id: int, **options) -> Dict:
        """启动浏览器"""
        
        profile = self.get_profile_by_id(user_id, profile_id)
        if not profile:
            raise ValueError("Profile not found")
        
        if not profile.can_launch:
            raise ValueError(f"Profile cannot be launched, current status: {profile.status}")
        
        try:
            async with adspower_client as client:
                adspower_response = await client.start_browser(
                    user_id=profile.adspower_id,
                    **options
                )
                
                if not client.is_success_response(adspower_response):
                    raise AdsPowerAPIError(client.get_error_message(adspower_response))
                
                browser_data = adspower_response["data"]
                
                # 更新状态
                profile.update_status("running")
                self.db.commit()
                
                logger.info(
                    "Browser started",
                    profile_id=profile.id,
                    adspower_id=profile.adspower_id
                )
                
                return browser_data
                
        except Exception as e:
            logger.error("Failed to start browser", error=str(e), profile_id=profile_id)
            raise
    
    async def stop_browser(self, user_id: int, profile_id: int) -> bool:
        """关闭浏览器"""
        
        profile = self.get_profile_by_id(user_id, profile_id)
        if not profile:
            raise ValueError("Profile not found")
        
        try:
            async with adspower_client as client:
                adspower_response = await client.stop_browser(profile.adspower_id)
                
                if not client.is_success_response(adspower_response):
                    logger.warning(
                        "Failed to stop browser via API",
                        error=client.get_error_message(adspower_response),
                        profile_id=profile_id
                    )
                
                # 更新状态
                profile.update_status("inactive")
                self.db.commit()
                
                logger.info(
                    "Browser stopped",
                    profile_id=profile.id,
                    adspower_id=profile.adspower_id
                )
                
                return True
                
        except Exception as e:
            logger.error("Failed to stop browser", error=str(e), profile_id=profile_id)
            raise
    
    async def check_proxy(self, user_id: int, profile_id: int) -> Dict:
        """检测代理"""
        
        profile = self.get_profile_by_id(user_id, profile_id)
        if not profile:
            raise ValueError("Profile not found")
        
        try:
            async with adspower_client as client:
                adspower_response = await client.check_proxy(profile.adspower_id)
                
                if not client.is_success_response(adspower_response):
                    raise AdsPowerAPIError(client.get_error_message(adspower_response))
                
                proxy_data = adspower_response["data"]
                
                logger.info(
                    "Proxy checked",
                    profile_id=profile.id,
                    status=proxy_data.get("status"),
                    latency=proxy_data.get("latency")
                )
                
                return proxy_data
                
        except Exception as e:
            logger.error("Failed to check proxy", error=str(e), profile_id=profile_id)
            raise
