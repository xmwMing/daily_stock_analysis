import apiClient from './index';

export interface ChatRequest {
  message: string;
  skills?: string[];
}

export interface ChatResponse {
  success: boolean;
  content: string;
  session_id: string;
  error?: string;
}

export interface StrategyInfo {
  id: string;
  name: string;
  description: string;
}

export interface StrategiesResponse {
  strategies: StrategyInfo[];
}

export const agentApi = {
  async chat(payload: ChatRequest): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/api/v1/agent/chat', payload, {
      timeout: 120000, // Agent analysis may take longer
    });
    return response.data;
  },
  async getStrategies(): Promise<StrategiesResponse> {
    const response = await apiClient.get<StrategiesResponse>('/api/v1/agent/strategies');
    return response.data;
  },
};
