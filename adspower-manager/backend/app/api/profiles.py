"""
环境管理API路由
"""
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.profile import Profile
from app.services.profile_service import ProfileService
from app.services.adspower_client import AdsPowerAPIError

router = APIRouter()


# Pydantic模型
class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    fingerprint: Optional[dict] = Field(default_factory=dict)
    proxy_config: Optional[dict] = Field(default_factory=dict)
    browser_config: Optional[dict] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)
    group_name: Optional[str] = Field(None, max_length=100)
    adspower_params: Optional[dict] = Field(default_factory=dict)


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    fingerprint: Optional[dict] = None
    proxy_config: Optional[dict] = None
    browser_config: Optional[dict] = None
    tags: Optional[List[str]] = None
    group_name: Optional[str] = Field(None, max_length=100)
    adspower_params: Optional[dict] = Field(default_factory=dict)


class ProfileResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    adspower_id: Optional[str]
    status: str
    is_active: bool
    tags: List[str]
    group_name: Optional[str]
    launch_count: int
    last_launched_at: Optional[str]
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class BatchProfileCreate(BaseModel):
    profiles: List[ProfileCreate] = Field(..., max_items=1000)


class BrowserStartOptions(BaseModel):
    headless: int = Field(0, ge=0, le=1)
    ip_tab: int = Field(0, ge=0, le=1)
    disable_password_filling: int = Field(0, ge=0, le=1)
    clear_cache_after_closing: int = Field(0, ge=0, le=1)
    enable_password_saving: int = Field(0, ge=0, le=1)
    cdp_mask: int = Field(0, ge=0, le=1)


class BrowserResponse(BaseModel):
    webdriver: Optional[str]
    ws_endpoint: Optional[str]
    debug_port: Optional[int]
    status: str


class ProxyCheckResponse(BaseModel):
    status: str
    ip: Optional[str]
    country: Optional[str]
    region: Optional[str]
    city: Optional[str]
    latency: Optional[int]


@router.get("/", response_model=List[ProfileResponse])
async def get_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, max_length=100),
    status: Optional[str] = Query(None),
    group_name: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取环境列表"""
    
    service = ProfileService(db)
    profiles = service.get_profiles(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        search=search,
        status=status,
        group_name=group_name,
        tags=tags
    )
    
    return [ProfileResponse.from_orm(profile) for profile in profiles]


@router.post("/", response_model=ProfileResponse)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """创建浏览器环境"""
    
    service = ProfileService(db)
    
    try:
        profile = await service.create_profile(
            user_id=current_user.id,
            **profile_data.dict()
        )
        return ProfileResponse.from_orm(profile)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AdsPowerAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AdsPower API error: {e.message}"
        )


@router.post("/batch", response_model=List[ProfileResponse])
async def batch_create_profiles(
    batch_data: BatchProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """批量创建环境"""
    
    service = ProfileService(db)
    
    try:
        profiles_data = [profile.dict() for profile in batch_data.profiles]
        profiles = await service.batch_create_profiles(
            user_id=current_user.id,
            profiles_data=profiles_data
        )
        return [ProfileResponse.from_orm(profile) for profile in profiles]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AdsPowerAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AdsPower API error: {e.message}"
        )


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取环境详情"""
    
    service = ProfileService(db)
    profile = service.get_profile_by_id(current_user.id, profile_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return ProfileResponse.from_orm(profile)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """更新环境配置"""
    
    service = ProfileService(db)
    
    try:
        # 只更新非None的字段
        update_data = {k: v for k, v in profile_data.dict().items() if v is not None}
        
        profile = await service.update_profile(
            user_id=current_user.id,
            profile_id=profile_id,
            **update_data
        )
        return ProfileResponse.from_orm(profile)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AdsPowerAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AdsPower API error: {e.message}"
        )


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """删除环境"""
    
    service = ProfileService(db)
    
    try:
        success = await service.delete_profile(current_user.id, profile_id)
        if success:
            return {"message": "Profile deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete profile"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AdsPowerAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AdsPower API error: {e.message}"
        )


@router.post("/{profile_id}/start", response_model=BrowserResponse)
async def start_browser(
    profile_id: int,
    options: BrowserStartOptions = BrowserStartOptions(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """启动浏览器"""
    
    service = ProfileService(db)
    
    try:
        browser_data = await service.start_browser(
            user_id=current_user.id,
            profile_id=profile_id,
            **options.dict()
        )
        
        return BrowserResponse(
            webdriver=browser_data.get("webdriver"),
            ws_endpoint=browser_data.get("ws", {}).get("puppeteer"),
            debug_port=browser_data.get("debug_port"),
            status="running"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AdsPowerAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AdsPower API error: {e.message}"
        )


@router.post("/{profile_id}/stop")
async def stop_browser(
    profile_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """关闭浏览器"""
    
    service = ProfileService(db)
    
    try:
        success = await service.stop_browser(current_user.id, profile_id)
        if success:
            return {"message": "Browser stopped successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop browser"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AdsPowerAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AdsPower API error: {e.message}"
        )


@router.get("/{profile_id}/proxy/check", response_model=ProxyCheckResponse)
async def check_proxy(
    profile_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """检测代理"""
    
    service = ProfileService(db)
    
    try:
        proxy_data = await service.check_proxy(current_user.id, profile_id)
        
        return ProxyCheckResponse(
            status=proxy_data.get("status", "unknown"),
            ip=proxy_data.get("ip"),
            country=proxy_data.get("country"),
            region=proxy_data.get("region"),
            city=proxy_data.get("city"),
            latency=proxy_data.get("latency")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AdsPowerAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AdsPower API error: {e.message}"
        )
