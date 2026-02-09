import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  HistoryListResponse,
  HistoryItem,
  HistoryFilters,
  AnalysisReport,
  NewsIntelResponse,
  NewsIntelItem,
} from '../types/analysis';

// ============ API 接口 ============

export interface GetHistoryListParams extends HistoryFilters {
  page?: number;
  limit?: number;
}

export const historyApi = {
  /**
   * 获取历史分析列表
   * @param params 筛选和分页参数
   */
  getList: async (params: GetHistoryListParams = {}): Promise<HistoryListResponse> => {
    const { stockCode, startDate, endDate, page = 1, limit = 20 } = params;

    const queryParams: Record<string, string | number> = { page, limit };
    if (stockCode) queryParams.stock_code = stockCode;
    if (startDate) queryParams.start_date = startDate;
    if (endDate) queryParams.end_date = endDate;

    const response = await apiClient.get<Record<string, unknown>>('/api/v1/history', {
      params: queryParams,
    });

    const data = toCamelCase<{ total: number; page: number; limit: number; items: HistoryItem[] }>(response.data);
    return {
      total: data.total,
      page: data.page,
      limit: data.limit,
      items: data.items.map(item => toCamelCase<HistoryItem>(item)),
    };
  },

  /**
   * 获取历史报告详情
   * @param queryId 分析记录唯一标识
   */
  getDetail: async (queryId: string): Promise<AnalysisReport> => {
    const response = await apiClient.get<Record<string, unknown>>(`/api/v1/history/${queryId}`);
    return toCamelCase<AnalysisReport>(response.data);
  },

  /**
   * 获取历史报告关联新闻
   * @param queryId 分析记录唯一标识
   * @param limit 返回数量限制
   */
  getNews: async (queryId: string, limit = 20): Promise<NewsIntelResponse> => {
    const response = await apiClient.get<Record<string, unknown>>(`/api/v1/history/${queryId}/news`, {
      params: { limit },
    });

    const data = toCamelCase<NewsIntelResponse>(response.data);
    return {
      total: data.total,
      items: (data.items || []).map(item => toCamelCase<NewsIntelItem>(item)),
    };
  },
};
