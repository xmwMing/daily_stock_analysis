import type React from 'react';
import { useState, useEffect, useCallback, useRef } from 'react';
import type { HistoryItem, AnalysisReport, TaskInfo } from '../types/analysis';
import { historyApi } from '../api/history';
import { analysisApi, DuplicateTaskError } from '../api/analysis';
import { validateStockCode } from '../utils/validation';
import { getRecentStartDate, toDateInputValue } from '../utils/format';
import { useAnalysisStore } from '../stores/analysisStore';
import { ReportSummary } from '../components/report';
import { HistoryList } from '../components/history';
import { TaskPanel } from '../components/tasks';
import { useTaskStream } from '../hooks';

/**
 * 首页 - 单页设计
 * 顶部输入 + 左侧历史 + 右侧报告
 */
const HomePage: React.FC = () => {
  const { setLoading, setError: setStoreError } = useAnalysisStore();

  // 输入状态
  const [stockCode, setStockCode] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [inputError, setInputError] = useState<string>();

// 历史列表状态
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  // 报告详情状态
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);
  const [isLoadingReport, setIsLoadingReport] = useState(false);

  // 任务队列状态
  const [activeTasks, setActiveTasks] = useState<TaskInfo[]>([]);
  const [duplicateError, setDuplicateError] = useState<string | null>(null);

  // 用于跟踪当前分析请求，避免竞态条件
  const analysisRequestIdRef = useRef<number>(0);

  // 更新任务列表中的任务
  const updateTask = useCallback((updatedTask: TaskInfo) => {
    setActiveTasks((prev) => {
      const index = prev.findIndex((t) => t.taskId === updatedTask.taskId);
      if (index >= 0) {
        const newTasks = [...prev];
        newTasks[index] = updatedTask;
        return newTasks;
      }
      return prev;
    });
  }, []);

  // 移除已完成/失败的任务
  const removeTask = useCallback((taskId: string) => {
    setActiveTasks((prev) => prev.filter((t) => t.taskId !== taskId));
  }, []);

  // SSE 任务流
  useTaskStream({
    onTaskCreated: (task) => {
      setActiveTasks((prev) => {
        // 避免重复添加
        if (prev.some((t) => t.taskId === task.taskId)) return prev;
        return [...prev, task];
      });
    },
    onTaskStarted: updateTask,
    onTaskCompleted: (task) => {
      // 刷新历史列表
      fetchHistory();
      // 延迟移除任务，让用户看到完成状态
      setTimeout(() => removeTask(task.taskId), 2000);
    },
    onTaskFailed: (task) => {
      updateTask(task);
      // 显示错误提示
      setStoreError(task.error || '分析失败');
      // 延迟移除任务
      setTimeout(() => removeTask(task.taskId), 5000);
    },
    onError: () => {
      console.warn('SSE 连接断开，正在重连...');
    },
    enabled: true,
  });

// 加载历史列表
  const fetchHistory = useCallback(async (autoSelectFirst = false, reset = true) => {
    if (reset) {
      setIsLoadingHistory(true);
      setCurrentPage(1);
    } else {
      setIsLoadingMore(true);
    }

    const page = reset ? 1 : currentPage + 1;

    try {
      const response = await historyApi.getList({
        startDate: getRecentStartDate(30),
        endDate: toDateInputValue(new Date()),
        page,
        limit: pageSize,
      });

      if (reset) {
        setHistoryItems(response.items);
      } else {
        setHistoryItems(prev => [...prev, ...response.items]);
      }

      // 判断是否还有更多数据
      const totalLoaded = reset ? response.items.length : historyItems.length + response.items.length;
      setHasMore(totalLoaded < response.total);
      setCurrentPage(page);

      // 如果需要自动选择第一条，且有数据，且当前没有选中报告
      if (autoSelectFirst && response.items.length > 0 && !selectedReport) {
        const firstItem = response.items[0];
        setIsLoadingReport(true);
        try {
          const report = await historyApi.getDetail(firstItem.queryId);
          setSelectedReport(report);
        } catch (err) {
          console.error('Failed to fetch first report:', err);
        } finally {
          setIsLoadingReport(false);
        }
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setIsLoadingHistory(false);
      setIsLoadingMore(false);
    }
  }, [selectedReport, currentPage, historyItems.length, pageSize]);

  // 加载更多历史记录
  const handleLoadMore = useCallback(() => {
    if (!isLoadingMore && hasMore) {
      fetchHistory(false, false);
    }
  }, [fetchHistory, isLoadingMore, hasMore]);

  // 初始加载 - 自动选择第一条
  useEffect(() => {
    fetchHistory(true);
  }, []);

  // 点击历史项加载报告
  const handleHistoryClick = async (queryId: string) => {
    // 取消当前分析请求的结果显示（通过递增 requestId）
    analysisRequestIdRef.current += 1;

    setIsLoadingReport(true);
    try {
      const report = await historyApi.getDetail(queryId);
      setSelectedReport(report);
    } catch (err) {
      console.error('Failed to fetch report:', err);
    } finally {
      setIsLoadingReport(false);
    }
  };

  // 分析股票（异步模式）
  const handleAnalyze = async () => {
    const { valid, message, normalized } = validateStockCode(stockCode);
    if (!valid) {
      setInputError(message);
      return;
    }

    setInputError(undefined);
    setDuplicateError(null);
    setIsAnalyzing(true);
    setLoading(true);
    setStoreError(null);

    // 记录当前请求的 ID
    const currentRequestId = ++analysisRequestIdRef.current;

    try {
      // 使用异步模式提交分析
      const response = await analysisApi.analyzeAsync({
        stockCode: normalized,
        reportType: 'detailed',
      });

      // 清空输入框
      if (currentRequestId === analysisRequestIdRef.current) {
        setStockCode('');
      }

      // 任务已提交，SSE 会推送更新
      console.log('Task submitted:', response.taskId);
    } catch (err) {
      console.error('Analysis failed:', err);
      if (currentRequestId === analysisRequestIdRef.current) {
        if (err instanceof DuplicateTaskError) {
          // 显示重复任务错误
          setDuplicateError(`股票 ${err.stockCode} 正在分析中，请等待完成`);
        } else {
          setStoreError(err instanceof Error ? err.message : '分析失败');
        }
      }
    } finally {
      setIsAnalyzing(false);
      setLoading(false);
    }
  };

  // 回车提交
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && stockCode && !isAnalyzing) {
      handleAnalyze();
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* 顶部输入栏 */}
      <header className="flex-shrink-0 px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2 max-w-2xl">
          <div className="flex-1 relative">
            <input
              type="text"
              value={stockCode}
              onChange={(e) => {
                setStockCode(e.target.value.toUpperCase());
                setInputError(undefined);
              }}
              onKeyDown={handleKeyDown}
              placeholder="输入股票代码，如 600519、00700、AAPL"
              disabled={isAnalyzing}
              className={`input-terminal w-full ${inputError ? 'border-danger/50' : ''}`}
            />
            {inputError && (
              <p className="absolute -bottom-4 left-0 text-xs text-danger">{inputError}</p>
            )}
            {duplicateError && (
              <p className="absolute -bottom-4 left-0 text-xs text-warning">{duplicateError}</p>
            )}
          </div>
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!stockCode || isAnalyzing}
            className="btn-primary flex items-center gap-1.5 whitespace-nowrap"
          >
            {isAnalyzing ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                分析中
              </>
            ) : (
              '分析'
            )}
          </button>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 flex overflow-hidden p-3 gap-3">
{/* 左侧：任务面板 + 历史列表 */}
        <div className="flex flex-col gap-3 w-64 flex-shrink-0 overflow-hidden">
          {/* 任务面板 */}
          <TaskPanel tasks={activeTasks} />

          {/* 历史列表 */}
          <HistoryList
            items={historyItems}
            isLoading={isLoadingHistory}
            isLoadingMore={isLoadingMore}
            hasMore={hasMore}
            selectedQueryId={selectedReport?.meta.queryId}
            onItemClick={handleHistoryClick}
            onLoadMore={handleLoadMore}
            className="max-h-[62vh] overflow-hidden"
          />
        </div>

        {/* 右侧报告详情 */}
        <section className="flex-1 overflow-y-auto pl-1">
          {isLoadingReport ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="w-10 h-10 border-3 border-cyan/20 border-t-cyan rounded-full animate-spin" />
              <p className="mt-3 text-secondary text-sm">加载报告中...</p>
            </div>
          ) : selectedReport ? (
            <div className="max-w-4xl">
              {/* 报告内容 */}
              <ReportSummary data={selectedReport} isHistory />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-12 h-12 mb-3 rounded-xl bg-elevated flex items-center justify-center">
                <svg className="w-6 h-6 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-base font-medium text-white mb-1.5">开始分析</h3>
              <p className="text-xs text-muted max-w-xs">
                输入股票代码进行分析，或从左侧选择历史报告查看
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default HomePage;
