# AdsPower Manager 用户指南

## 📖 目录

1. [快速开始](#快速开始)
2. [环境管理](#环境管理)
3. [RPA流程设计](#rpa流程设计)
4. [任务管理](#任务管理)
5. [监控面板](#监控面板)
6. [常见问题](#常见问题)

## 🚀 快速开始

### 系统要求

- **操作系统**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **浏览器**: Chrome 90+, Firefox 88+, Safari 14+
- **AdsPower客户端**: 最新版本
- **网络**: 稳定的互联网连接

### 首次登录

1. 打开浏览器访问系统地址
2. 使用管理员提供的账号密码登录
3. 首次登录建议修改密码

### 界面概览

系统主界面包含以下模块：

- **仪表板**: 系统概览和统计信息
- **环境管理**: AdsPower浏览器环境管理
- **RPA设计器**: 可视化流程设计
- **任务监控**: 任务执行状态监控
- **设置**: 个人设置和系统配置

## 🌐 环境管理

### 创建浏览器环境

1. 进入"环境管理"页面
2. 点击"新建环境"按钮
3. 填写环境信息：
   - **环境名称**: 便于识别的名称
   - **描述**: 环境用途说明
   - **分组**: 选择或创建分组
   - **标签**: 添加标签便于筛选

4. 配置指纹参数：
   - **操作系统**: Windows/macOS/Linux
   - **浏览器版本**: Chrome版本
   - **屏幕分辨率**: 显示器分辨率
   - **时区**: 地理位置时区
   - **语言**: 浏览器语言

5. 配置代理（可选）：
   - **代理类型**: HTTP/HTTPS/SOCKS5
   - **服务器地址**: 代理服务器IP
   - **端口**: 代理端口
   - **认证**: 用户名和密码

6. 点击"创建"完成

### 批量创建环境

1. 点击"批量创建"按钮
2. 选择创建方式：
   - **Excel导入**: 下载模板，填写后上传
   - **手动配置**: 设置数量和参数范围
3. 预览配置信息
4. 确认创建

### 环境操作

#### 启动浏览器
- 点击环境列表中的"启动"按钮
- 系统会自动打开AdsPower浏览器
- 浏览器会应用配置的指纹和代理

#### 环境管理
- **编辑**: 修改环境配置
- **复制**: 基于现有环境创建新环境
- **删除**: 删除不需要的环境
- **导出**: 导出环境配置

#### 代理检测
- 点击"检测代理"查看代理状态
- 显示IP地址、地理位置、延迟等信息
- 支持批量检测多个环境

## 🤖 RPA流程设计

### 流程设计器界面

RPA设计器采用拖拽式可视化设计：

- **节点面板**: 左侧显示所有可用节点
- **画布区域**: 中央流程设计区域
- **属性面板**: 右侧节点配置面板
- **工具栏**: 顶部操作工具

### 基础操作

#### 添加节点
1. 从左侧节点面板拖拽节点到画布
2. 或双击节点自动添加到画布
3. 节点会自动连接到流程中

#### 连接节点
1. 点击节点的输出端口
2. 拖拽到目标节点的输入端口
3. 建立节点间的执行顺序

#### 配置节点
1. 选中节点
2. 在右侧属性面板配置参数
3. 支持变量引用和表达式

### 常用节点说明

#### 页面操作节点

**访问网址 (gotoUrl)**
- 功能: 在浏览器中打开指定网址
- 参数:
  - `url`: 目标网址 (必填)
  - `timeout`: 超时时间 (可选，默认30秒)

**点击元素 (click)**
- 功能: 点击页面上的指定元素
- 参数:
  - `selector`: CSS选择器 (必填)
  - `serial`: 是否串行执行 (可选)

**输入文本 (input)**
- 功能: 在输入框中输入文本
- 参数:
  - `selector`: CSS选择器 (必填)
  - `text`: 输入内容 (必填)

#### 数据处理节点

**设置变量 (setVariable)**
- 功能: 设置流程变量
- 参数:
  - `name`: 变量名 (必填)
  - `value`: 变量值 (必填)

**提取文本 (extractTxt)**
- 功能: 从页面元素提取文本
- 参数:
  - `selector`: CSS选择器 (必填)
  - `variable`: 存储变量名 (必填)

#### 流程控制节点

**条件判断 (ifCondition)**
- 功能: 根据条件执行不同分支
- 参数:
  - `leftValue`: 左值
  - `operator`: 比较操作符
  - `rightValue`: 右值

**等待时间 (waitTime)**
- 功能: 暂停执行指定时间
- 参数:
  - `timeout`: 等待时间(毫秒)
  - `timeoutType`: 固定时间或随机区间

### 变量系统

#### 变量定义
- 在流程设置中定义全局变量
- 使用`${变量名}`语法引用变量
- 支持字符串、数字、布尔值、对象类型

#### 变量作用域
- **全局变量**: 整个流程可用
- **节点变量**: 节点执行时设置
- **系统变量**: 系统自动提供

#### 常用系统变量
- `${current_time}`: 当前时间
- `${random_number}`: 随机数
- `${profile_name}`: 当前环境名称

### 流程调试

#### 单步执行
1. 点击"调试"按钮
2. 流程会逐节点执行
3. 可以查看每个节点的执行结果

#### 断点设置
1. 在需要暂停的位置添加"断点"节点
2. 执行到断点时会暂停
3. 可以检查变量值和页面状态

## 📋 任务管理

### 创建任务

1. 进入"任务管理"页面
2. 点击"新建任务"
3. 选择执行环境和RPA流程
4. 配置任务参数：
   - **任务名称**: 便于识别
   - **描述**: 任务说明
   - **优先级**: 1-10，数字越大优先级越高
   - **变量**: 覆盖流程默认变量
   - **调度**: 立即执行或定时执行

### 任务执行

#### 立即执行
- 创建后自动开始执行
- 可在任务列表查看实时状态

#### 定时执行
- 设置执行时间
- 支持一次性和周期性任务

#### 批量执行
- 选择多个任务
- 点击"批量执行"
- 系统会按优先级和并发限制执行

### 任务监控

#### 实时状态
- **等待中**: 任务已创建，等待执行
- **执行中**: 任务正在运行
- **已完成**: 任务成功完成
- **失败**: 任务执行失败
- **已取消**: 手动取消的任务

#### 进度跟踪
- 显示当前执行节点
- 实时更新执行进度
- 支持WebSocket实时推送

#### 日志查看
1. 点击任务的"查看日志"
2. 显示详细执行日志
3. 包含每个节点的执行信息
4. 错误信息和调试信息

### 任务操作

#### 重试任务
- 失败的任务可以重试
- 系统支持自动重试机制
- 可设置最大重试次数

#### 取消任务
- 正在执行的任务可以取消
- 会立即停止执行
- 释放占用的资源

## 📊 监控面板

### 系统概览

仪表板显示系统整体状态：

- **环境统计**: 总数、活跃数、状态分布
- **任务统计**: 今日执行、成功率、失败率
- **系统资源**: CPU、内存、磁盘使用率
- **实时连接**: WebSocket连接数

### 性能监控

#### 系统指标
- **CPU使用率**: 实时CPU占用
- **内存使用率**: 内存占用情况
- **磁盘空间**: 存储空间使用
- **网络流量**: 网络IO统计

#### 应用指标
- **API响应时间**: 接口性能
- **任务执行时长**: 平均执行时间
- **错误率**: 系统错误统计
- **并发数**: 同时执行任务数

### 告警通知

#### 告警规则
系统预设多种告警规则：
- CPU使用率超过80%
- 内存使用率超过85%
- 磁盘空间不足10%
- 任务失败率超过20%

#### 通知方式
- **页面通知**: 实时弹窗提醒
- **邮件通知**: 发送告警邮件
- **WebSocket推送**: 实时状态更新

## ❓ 常见问题

### 环境相关

**Q: 环境创建失败怎么办？**
A: 
1. 检查AdsPower客户端是否正常运行
2. 确认API连接配置正确
3. 查看错误日志获取详细信息

**Q: 代理检测失败？**
A: 
1. 确认代理服务器可用
2. 检查代理配置参数
3. 验证网络连接

**Q: 浏览器启动慢？**
A: 
1. 检查系统资源使用情况
2. 减少同时启动的浏览器数量
3. 优化指纹配置参数

### RPA相关

**Q: 节点执行失败？**
A: 
1. 检查页面元素是否存在
2. 确认CSS选择器正确
3. 增加等待时间

**Q: 变量引用错误？**
A: 
1. 确认变量名拼写正确
2. 检查变量作用域
3. 使用`${}`语法引用

**Q: 流程执行超时？**
A: 
1. 增加节点超时时间
2. 优化流程逻辑
3. 检查网络连接

### 任务相关

**Q: 任务排队时间长？**
A: 
1. 调整任务优先级
2. 增加并发执行数量
3. 优化任务调度策略

**Q: 任务执行失败率高？**
A: 
1. 检查RPA流程稳定性
2. 优化错误处理逻辑
3. 增加重试机制

### 系统相关

**Q: 页面加载慢？**
A: 
1. 检查网络连接
2. 清理浏览器缓存
3. 联系管理员检查服务器

**Q: WebSocket连接断开？**
A: 
1. 刷新页面重新连接
2. 检查网络稳定性
3. 确认防火墙设置

## 📞 技术支持

如遇到其他问题，请联系技术支持：

- **邮箱**: alex04058888@icloud.com
- **文档**: 查看在线文档获取更多信息
- **日志**: 提供详细错误日志以便快速定位问题

---

*本文档会持续更新，请关注最新版本*
