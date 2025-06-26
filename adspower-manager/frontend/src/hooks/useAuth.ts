/**
 * 认证相关Hook
 */
import { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '@/store';
import { setUser, clearUser } from '@/store/slices/authSlice';
import { authService } from '@/services/authService';
import { User } from '@/types/api';

export const useAuth = () => {
  const dispatch = useDispatch();
  const { user, isAuthenticated } = useSelector((state: RootState) => state.auth);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setLoading(false);
        return;
      }

      // 验证token并获取用户信息
      const userData = await authService.getCurrentUser();
      dispatch(setUser(userData));
    } catch (error) {
      // Token无效，清除本地存储
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      dispatch(clearUser());
    } finally {
      setLoading(false);
    }
  };

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const response = await authService.login(username, password);
      
      // 保存token
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
      
      // 获取用户信息
      const userData = await authService.getCurrentUser();
      dispatch(setUser(userData));
      
      return true;
    } catch (error) {
      return false;
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // 清除本地数据
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      dispatch(clearUser());
    }
  };

  const register = async (userData: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
  }): Promise<boolean> => {
    try {
      await authService.register(userData);
      return true;
    } catch (error) {
      return false;
    }
  };

  return {
    user,
    isAuthenticated,
    loading,
    login,
    logout,
    register,
    checkAuthStatus,
  };
};
