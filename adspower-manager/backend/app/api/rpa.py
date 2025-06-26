"""
RPA流程管理API
"""
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.rpa import RPAFlow

router = APIRouter()


# Pydantic模型
class RPAFlowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=50)
    nodes: List[dict] = Field(..., min_items=1)
    variables: Optional[dict] = Field(default_factory=dict)
    settings: Optional[dict] = Field(default_factory=dict)
    is_template: bool = Field(False)


class RPAFlowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=50)
    nodes: Optional[List[dict]] = None
    variables: Optional[dict] = None
    settings: Optional[dict] = None
    is_active: Optional[bool] = None
    is_template: Optional[bool] = None


class RPAFlowResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    nodes: List[dict]
    variables: dict
    settings: dict
    version: int
    is_active: bool
    is_template: bool
    execution_count: int
    success_count: int
    failure_count: int
    success_rate: float
    node_count: int
    last_executed_at: Optional[str]
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class RPANodeTemplate(BaseModel):
    type: str
    name: str
    description: str
    config_schema: dict
    category: str


@router.get("/flows", response_model=List[RPAFlowResponse])
async def get_rpa_flows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, max_length=100),
    category: Optional[str] = Query(None),
    is_template: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取RPA流程列表"""
    
    query = db.query(RPAFlow).filter(RPAFlow.user_id == current_user.id)
    
    # 搜索过滤
    if search:
        query = query.filter(
            RPAFlow.name.ilike(f"%{search}%") |
            RPAFlow.description.ilike(f"%{search}%")
        )
    
    # 分类过滤
    if category:
        query = query.filter(RPAFlow.category == category)
    
    # 模板过滤
    if is_template is not None:
        query = query.filter(RPAFlow.is_template == is_template)
    
    flows = query.offset(skip).limit(limit).all()
    return [RPAFlowResponse.from_orm(flow) for flow in flows]


@router.post("/flows", response_model=RPAFlowResponse)
async def create_rpa_flow(
    flow_data: RPAFlowCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """创建RPA流程"""
    
    # 检查名称是否重复
    existing = db.query(RPAFlow).filter(
        RPAFlow.user_id == current_user.id,
        RPAFlow.name == flow_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flow name already exists"
        )
    
    # 验证节点格式
    if not _validate_nodes(flow_data.nodes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid nodes format"
        )
    
    # 创建流程
    flow = RPAFlow(
        user_id=current_user.id,
        name=flow_data.name,
        description=flow_data.description,
        category=flow_data.category,
        nodes=flow_data.nodes,
        variables=flow_data.variables,
        settings=flow_data.settings,
        is_template=flow_data.is_template,
        version=1,
        is_active=True
    )
    
    db.add(flow)
    db.commit()
    db.refresh(flow)
    
    return RPAFlowResponse.from_orm(flow)


@router.get("/flows/{flow_id}", response_model=RPAFlowResponse)
async def get_rpa_flow(
    flow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取RPA流程详情"""
    
    flow = db.query(RPAFlow).filter(
        RPAFlow.id == flow_id,
        RPAFlow.user_id == current_user.id
    ).first()
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found"
        )
    
    return RPAFlowResponse.from_orm(flow)


@router.put("/flows/{flow_id}", response_model=RPAFlowResponse)
async def update_rpa_flow(
    flow_id: int,
    flow_data: RPAFlowUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """更新RPA流程"""
    
    flow = db.query(RPAFlow).filter(
        RPAFlow.id == flow_id,
        RPAFlow.user_id == current_user.id
    ).first()
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found"
        )
    
    # 验证节点格式（如果提供）
    if flow_data.nodes and not _validate_nodes(flow_data.nodes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid nodes format"
        )
    
    # 更新字段
    update_data = flow_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(flow, key, value)
    
    # 如果更新了节点，增加版本号
    if flow_data.nodes:
        flow.version += 1
    
    db.commit()
    db.refresh(flow)
    
    return RPAFlowResponse.from_orm(flow)


@router.delete("/flows/{flow_id}")
async def delete_rpa_flow(
    flow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """删除RPA流程"""
    
    flow = db.query(RPAFlow).filter(
        RPAFlow.id == flow_id,
        RPAFlow.user_id == current_user.id
    ).first()
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found"
        )
    
    # 检查是否有正在运行的任务
    from app.models.task import Task
    running_tasks = db.query(Task).filter(
        Task.rpa_flow_id == flow_id,
        Task.status == "running"
    ).count()
    
    if running_tasks > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete flow with running tasks"
        )
    
    db.delete(flow)
    db.commit()
    
    return {"message": "Flow deleted successfully"}


@router.post("/flows/{flow_id}/clone", response_model=RPAFlowResponse)
async def clone_rpa_flow(
    flow_id: int,
    new_name: str = Query(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """克隆RPA流程"""
    
    original_flow = db.query(RPAFlow).filter(
        RPAFlow.id == flow_id,
        RPAFlow.user_id == current_user.id
    ).first()
    
    if not original_flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found"
        )
    
    # 检查新名称是否重复
    existing = db.query(RPAFlow).filter(
        RPAFlow.user_id == current_user.id,
        RPAFlow.name == new_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flow name already exists"
        )
    
    # 创建克隆
    cloned_flow = RPAFlow(
        user_id=current_user.id,
        name=new_name,
        description=f"Cloned from {original_flow.name}",
        category=original_flow.category,
        nodes=original_flow.nodes.copy(),
        variables=original_flow.variables.copy(),
        settings=original_flow.settings.copy(),
        is_template=False,
        version=1,
        is_active=True
    )
    
    db.add(cloned_flow)
    db.commit()
    db.refresh(cloned_flow)
    
    return RPAFlowResponse.from_orm(cloned_flow)


@router.get("/node-templates", response_model=List[RPANodeTemplate])
async def get_node_templates() -> Any:
    """获取RPA节点模板"""
    
    templates = [
        {
            "type": "newPage",
            "name": "新建标签页",
            "description": "在当前浏览器中新开一个标签页",
            "config_schema": {},
            "category": "页面操作"
        },
        {
            "type": "gotoUrl",
            "name": "访问网址",
            "description": "在地址栏输入指定URL并加载",
            "config_schema": {
                "url": {"type": "string", "required": True, "description": "目标网址"},
                "timeout": {"type": "integer", "default": 30000, "description": "超时时间(毫秒)"}
            },
            "category": "页面操作"
        },
        {
            "type": "click",
            "name": "点击元素",
            "description": "点击页面上的指定元素",
            "config_schema": {
                "selector": {"type": "string", "required": True, "description": "CSS选择器"},
                "serial": {"type": "boolean", "default": False, "description": "是否串行执行"}
            },
            "category": "页面操作"
        },
        {
            "type": "input",
            "name": "输入文本",
            "description": "在指定输入框中输入文本",
            "config_schema": {
                "selector": {"type": "string", "required": True, "description": "CSS选择器"},
                "text": {"type": "string", "required": True, "description": "输入内容"}
            },
            "category": "页面操作"
        },
        {
            "type": "waitTime",
            "name": "等待时间",
            "description": "等待指定时间",
            "config_schema": {
                "timeoutType": {"type": "string", "enum": ["fixed", "randomInterval"], "default": "fixed"},
                "timeout": {"type": "integer", "description": "等待时间(毫秒)"},
                "timeoutMin": {"type": "integer", "description": "最小等待时间(毫秒)"},
                "timeoutMax": {"type": "integer", "description": "最大等待时间(毫秒)"}
            },
            "category": "等待操作"
        }
    ]
    
    return templates


def _validate_nodes(nodes: List[dict]) -> bool:
    """验证节点格式"""
    
    if not isinstance(nodes, list) or len(nodes) == 0:
        return False
    
    for node in nodes:
        if not isinstance(node, dict):
            return False
        
        if "type" not in node:
            return False
        
        if "config" not in node:
            node["config"] = {}
    
    return True
