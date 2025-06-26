/**
 * API相关类型定义
 */

// 通用API响应
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data?: T;
  error?: string;
  details?: string[];
  timestamp: string;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

// 用户相关
export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  full_name?: string;
  avatar_url?: string;
  phone?: string;
  created_at: string;
  updated_at?: string;
  last_login_at?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// 环境相关
export interface Profile {
  id: number;
  name: string;
  description?: string;
  adspower_id?: string;
  status: string;
  is_active: boolean;
  tags: string[];
  group_name?: string;
  launch_count: number;
  last_launched_at?: string;
  created_at: string;
  updated_at?: string;
  fingerprint?: Record<string, any>;
  proxy_config?: Record<string, any>;
  browser_config?: Record<string, any>;
}

export interface ProfileCreateRequest {
  name: string;
  description?: string;
  fingerprint?: Record<string, any>;
  proxy_config?: Record<string, any>;
  browser_config?: Record<string, any>;
  tags?: string[];
  group_name?: string;
  adspower_params?: Record<string, any>;
}

export interface BrowserStartOptions {
  headless?: number;
  ip_tab?: number;
  disable_password_filling?: number;
  clear_cache_after_closing?: number;
  enable_password_saving?: number;
  cdp_mask?: number;
}

export interface BrowserResponse {
  webdriver?: string;
  ws_endpoint?: string;
  debug_port?: number;
  status: string;
}

export interface ProxyCheckResponse {
  status: string;
  ip?: string;
  country?: string;
  region?: string;
  city?: string;
  latency?: number;
}

// RPA相关
export interface RPANode {
  type: string;
  config: Record<string, any>;
  position?: { x: number; y: number };
  connections?: {
    success?: string[];
    error?: string[];
  };
}

export interface RPAFlow {
  id: number;
  name: string;
  description?: string;
  category?: string;
  nodes: RPANode[];
  variables: Record<string, any>;
  settings: Record<string, any>;
  version: number;
  is_active: boolean;
  is_template: boolean;
  execution_count: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  node_count: number;
  last_executed_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface RPAFlowCreateRequest {
  name: string;
  description?: string;
  category?: string;
  nodes: RPANode[];
  variables?: Record<string, any>;
  settings?: Record<string, any>;
  is_template?: boolean;
}

export interface RPANodeTemplate {
  type: string;
  name: string;
  description: string;
  config_schema: Record<string, any>;
  category: string;
}

// 任务相关
export interface Task {
  id: number;
  name?: string;
  description?: string;
  status: string;
  progress: number;
  current_node_index: number;
  result?: Record<string, any>;
  error_message?: string;
  error_node_index?: number;
  variables: Record<string, any>;
  settings: Record<string, any>;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  retry_count: number;
  max_retries: number;
  priority: number;
  created_at: string;
  updated_at?: string;
  profile_name?: string;
  rpa_flow_name?: string;
}

export interface TaskCreateRequest {
  profile_id: number;
  rpa_flow_id: number;
  name?: string;
  description?: string;
  variables?: Record<string, any>;
  settings?: Record<string, any>;
  scheduled_at?: string;
  priority?: number;
}

export interface TaskLogEntry {
  timestamp: string;
  level: string;
  message: string;
  node_index?: number;
}

// 查询参数
export interface ProfileQueryParams {
  skip?: number;
  limit?: number;
  search?: string;
  status?: string;
  group_name?: string;
  tags?: string[];
}

export interface RPAFlowQueryParams {
  skip?: number;
  limit?: number;
  search?: string;
  category?: string;
  is_template?: boolean;
}

export interface TaskQueryParams {
  skip?: number;
  limit?: number;
  status?: string;
  profile_id?: number;
  rpa_flow_id?: number;
}
