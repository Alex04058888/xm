/**
 * 认证服务
 */
import { request } from './api';
import { User, LoginRequest, LoginResponse } from '@/types/api';

export const authService = {
  /**
   * 用户登录
   */
  async login(username: string, password: string): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    return request.post('/auth/login', formData);
  },

  /**
   * 用户注册
   */
  async register(userData: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
  }): Promise<User> {
    return request.post('/auth/register', userData);
  },

  /**
   * 刷新令牌
   */
  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    return request.post('/auth/refresh', { refresh_token: refreshToken });
  },

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<User> {
    return request.get('/auth/me');
  },

  /**
   * 用户登出
   */
  async logout(): Promise<void> {
    return request.post('/auth/logout');
  },
};
