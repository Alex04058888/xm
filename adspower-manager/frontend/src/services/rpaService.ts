/**
 * RPA服务
 */
import { request } from './api';
import {
  RPAFlow,
  RPAFlowCreateRequest,
  RPAFlowQueryParams,
  RPANodeTemplate,
} from '@/types/api';

export const rpaService = {
  /**
   * 获取RPA流程列表
   */
  async getFlows(params?: RPAFlowQueryParams): Promise<RPAFlow[]> {
    return request.get('/rpa/flows', params);
  },

  /**
   * 创建RPA流程
   */
  async createFlow(flowData: RPAFlowCreateRequest): Promise<RPAFlow> {
    return request.post('/rpa/flows', flowData);
  },

  /**
   * 获取RPA流程详情
   */
  async getFlow(flowId: number): Promise<RPAFlow> {
    return request.get(`/rpa/flows/${flowId}`);
  },

  /**
   * 更新RPA流程
   */
  async updateFlow(flowId: number, flowData: Partial<RPAFlowCreateRequest>): Promise<RPAFlow> {
    return request.put(`/rpa/flows/${flowId}`, flowData);
  },

  /**
   * 删除RPA流程
   */
  async deleteFlow(flowId: number): Promise<void> {
    return request.delete(`/rpa/flows/${flowId}`);
  },

  /**
   * 克隆RPA流程
   */
  async cloneFlow(flowId: number, newName: string): Promise<RPAFlow> {
    return request.post(`/rpa/flows/${flowId}/clone?new_name=${encodeURIComponent(newName)}`);
  },

  /**
   * 获取RPA节点模板
   */
  async getNodeTemplates(): Promise<RPANodeTemplate[]> {
    return request.get('/rpa/node-templates');
  },
};
