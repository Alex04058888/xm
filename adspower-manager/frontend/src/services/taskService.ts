/**
 * 任务服务
 */
import { request } from './api';
import {
  Task,
  TaskCreateRequest,
  TaskQueryParams,
  TaskLogEntry,
} from '@/types/api';

export const taskService = {
  /**
   * 获取任务列表
   */
  async getTasks(params?: TaskQueryParams): Promise<Task[]> {
    return request.get('/tasks', params);
  },

  /**
   * 创建任务
   */
  async createTask(taskData: TaskCreateRequest): Promise<Task> {
    return request.post('/tasks', taskData);
  },

  /**
   * 获取任务详情
   */
  async getTask(taskId: number): Promise<Task> {
    return request.get(`/tasks/${taskId}`);
  },

  /**
   * 更新任务
   */
  async updateTask(taskId: number, taskData: Partial<TaskCreateRequest>): Promise<Task> {
    return request.put(`/tasks/${taskId}`, taskData);
  },

  /**
   * 删除任务
   */
  async deleteTask(taskId: number): Promise<void> {
    return request.delete(`/tasks/${taskId}`);
  },

  /**
   * 执行任务
   */
  async executeTask(taskId: number): Promise<void> {
    return request.post(`/tasks/${taskId}/execute`);
  },

  /**
   * 取消任务
   */
  async cancelTask(taskId: number): Promise<void> {
    return request.post(`/tasks/${taskId}/cancel`);
  },

  /**
   * 重试任务
   */
  async retryTask(taskId: number): Promise<void> {
    return request.post(`/tasks/${taskId}/retry`);
  },

  /**
   * 获取任务日志
   */
  async getTaskLogs(taskId: number): Promise<TaskLogEntry[]> {
    return request.get(`/tasks/${taskId}/logs`);
  },

  /**
   * 获取正在运行的任务状态
   */
  async getRunningTasksStatus(): Promise<{
    running_count: number;
    max_concurrent: number;
    running_task_ids: number[];
  }> {
    return request.get('/tasks/running/status');
  },
};
