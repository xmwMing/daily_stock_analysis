import type React from 'react';
import { useState, useEffect, useCallback } from 'react';
import { backtestApi } from '../api/backtest';
import { Card, Badge, Pagination } from '../components/common';
import type {
  BacktestResultItem,
  BacktestRunResponse,
  PerformanceMetrics,
} from '../types/backtest';

// ============ Helpers ============

function pct(value?: number | null): string {
  if (value == null) return '--';
  return `${value.toFixed(1)}%`;
}

function outcomeBadge(outcome?: string) {
  if (!outcome) return <Badge variant="default">--</Badge>;
  switch (outcome) {
    case 'win':
      return <Badge variant="success" glow>WIN</Badge>;
    case 'loss':
      return <Badge variant="danger" glow>LOSS</Badge>;
    case 'neutral':
      return <Badge variant="warning">NEUTRAL</Badge>;
    default:
      return <Badge variant="default">{outcome}</Badge>;
  }
}

function statusBadge(status: string) {
  switch (status) {
    case 'completed':
      return <Badge variant="success">completed</Badge>;
    case 'insufficient':
      return <Badge variant="warning">insufficient</Badge>;
    case 'error':
      return <Badge variant="danger">error</Badge>;
    default:
      return <Badge variant="default">{status}</Badge>;
  }
}

function boolIcon(value?: boolean | null) {
  if (value === true) return <span className="text-emerald-400">&#10003;</span>;
  if (value === false) return <span className="text-red-400">&#10007;</span>;
  return <span className="text-muted">--</span>;
}

// ============ Metric Row ============

const MetricRow: React.FC<{ label: string; value: string; accent?: boolean }> = ({ label, value, accent }) => (
  <div className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
    <span className="text-xs text-secondary">{label}</span>
    <span className={`text-sm font-mono font-semibold ${accent ? 'text-cyan' : 'text-white'}`}>{value}</span>
  </div>
);

// ============ Performance Card ============

const PerformanceCard: React.FC<{ metrics: PerformanceMetrics; title: string }> = ({ metrics, title }) => (
  <Card variant="gradient" padding="md" className="animate-fade-in">
    <div className="mb-3">
      <span className="label-uppercase">{title}</span>
    </div>
    <MetricRow label="Direction Accuracy" value={pct(metrics.directionAccuracyPct)} accent />
    <MetricRow label="Win Rate" value={pct(metrics.winRatePct)} accent />
    <MetricRow label="Avg Sim. Return" value={pct(metrics.avgSimulatedReturnPct)} />
    <MetricRow label="Avg Stock Return" value={pct(metrics.avgStockReturnPct)} />
    <MetricRow label="SL Trigger Rate" value={pct(metrics.stopLossTriggerRate)} />
    <MetricRow label="TP Trigger Rate" value={pct(metrics.takeProfitTriggerRate)} />
    <MetricRow label="Avg Days to Hit" value={metrics.avgDaysToFirstHit != null ? metrics.avgDaysToFirstHit.toFixed(1) : '--'} />
    <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between">
      <span className="text-xs text-muted">Evaluations</span>
      <span className="text-xs text-secondary font-mono">
        {Number(metrics.completedCount)} / {Number(metrics.totalEvaluations)}
      </span>
    </div>
    <div className="flex items-center justify-between">
      <span className="text-xs text-muted">W / L / N</span>
      <span className="text-xs font-mono">
        <span className="text-emerald-400">{metrics.winCount}</span>
        {' / '}
        <span className="text-red-400">{metrics.lossCount}</span>
        {' / '}
        <span className="text-amber-400">{metrics.neutralCount}</span>
      </span>
    </div>
  </Card>
);

// ============ Run Summary ============

const RunSummary: React.FC<{ data: BacktestRunResponse }> = ({ data }) => (
  <div className="flex items-center gap-4 px-3 py-2 rounded-lg bg-elevated border border-white/5 text-xs font-mono animate-fade-in">
    <span className="text-secondary">Processed: <span className="text-white">{data.processed}</span></span>
    <span className="text-secondary">Saved: <span className="text-cyan">{data.saved}</span></span>
    <span className="text-secondary">Completed: <span className="text-emerald-400">{data.completed}</span></span>
    <span className="text-secondary">Insufficient: <span className="text-amber-400">{data.insufficient}</span></span>
    {data.errors > 0 && (
      <span className="text-secondary">Errors: <span className="text-red-400">{data.errors}</span></span>
    )}
  </div>
);

// ============ Main Page ============

const BacktestPage: React.FC = () => {
  // Input state
  const [codeFilter, setCodeFilter] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<BacktestRunResponse | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  // Results state
  const [results, setResults] = useState<BacktestResultItem[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const pageSize = 20;

  // Performance state
  const [overallPerf, setOverallPerf] = useState<PerformanceMetrics | null>(null);
  const [stockPerf, setStockPerf] = useState<PerformanceMetrics | null>(null);
  const [isLoadingPerf, setIsLoadingPerf] = useState(false);

  // Fetch results
  const fetchResults = useCallback(async (page = 1, code?: string) => {
    setIsLoadingResults(true);
    try {
      const response = await backtestApi.getResults({ code: code || undefined, page, limit: pageSize });
      setResults(response.items);
      setTotalResults(response.total);
      setCurrentPage(response.page);
    } catch (err) {
      console.error('Failed to fetch backtest results:', err);
    } finally {
      setIsLoadingResults(false);
    }
  }, []);

  // Fetch performance
  const fetchPerformance = useCallback(async (code?: string) => {
    setIsLoadingPerf(true);
    try {
      const overall = await backtestApi.getOverallPerformance();
      setOverallPerf(overall);

      if (code) {
        const stock = await backtestApi.getStockPerformance(code);
        setStockPerf(stock);
      } else {
        setStockPerf(null);
      }
    } catch (err) {
      console.error('Failed to fetch performance:', err);
    } finally {
      setIsLoadingPerf(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchResults(1);
    fetchPerformance();
  }, [fetchResults, fetchPerformance]);

  // Run backtest
  const handleRun = async () => {
    setIsRunning(true);
    setRunResult(null);
    setRunError(null);
    try {
      const code = codeFilter.trim() || undefined;
      const response = await backtestApi.run({ code });
      setRunResult(response);
      // Refresh data
      fetchResults(1, codeFilter.trim() || undefined);
      fetchPerformance(codeFilter.trim() || undefined);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : 'Backtest failed');
    } finally {
      setIsRunning(false);
    }
  };

  // Filter by code
  const handleFilter = () => {
    const code = codeFilter.trim() || undefined;
    setCurrentPage(1);
    fetchResults(1, code);
    fetchPerformance(code);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleFilter();
    }
  };

  // Pagination
  const totalPages = Math.ceil(totalResults / pageSize);
  const handlePageChange = (page: number) => {
    fetchResults(page, codeFilter.trim() || undefined);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2 max-w-4xl">
          <div className="flex-1 relative">
            <input
              type="text"
              value={codeFilter}
              onChange={(e) => setCodeFilter(e.target.value.toUpperCase())}
              onKeyDown={handleKeyDown}
              placeholder="Filter by stock code (leave empty for all)"
              disabled={isRunning}
              className="input-terminal w-full"
            />
          </div>
          <button
            type="button"
            onClick={handleFilter}
            disabled={isLoadingResults}
            className="btn-secondary flex items-center gap-1.5 whitespace-nowrap"
          >
            Filter
          </button>
          <button
            type="button"
            onClick={handleRun}
            disabled={isRunning}
            className="btn-primary flex items-center gap-1.5 whitespace-nowrap"
          >
            {isRunning ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Running...
              </>
            ) : (
              'Run Backtest'
            )}
          </button>
        </div>
        {runResult && (
          <div className="mt-2 max-w-4xl">
            <RunSummary data={runResult} />
          </div>
        )}
        {runError && (
          <p className="mt-2 text-xs text-danger">{runError}</p>
        )}
      </header>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden p-3 gap-3">
        {/* Left sidebar - Performance */}
        <div className="flex flex-col gap-3 w-64 flex-shrink-0 overflow-y-auto">
          {isLoadingPerf ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-8 h-8 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
            </div>
          ) : overallPerf ? (
            <PerformanceCard metrics={overallPerf} title="Overall Performance" />
          ) : (
            <Card padding="md">
              <p className="text-xs text-muted text-center py-4">
                No backtest data yet. Run a backtest to see performance metrics.
              </p>
            </Card>
          )}

          {stockPerf && (
            <PerformanceCard metrics={stockPerf} title={`${stockPerf.code || codeFilter}`} />
          )}
        </div>

        {/* Right content - Results table */}
        <section className="flex-1 overflow-y-auto">
          {isLoadingResults ? (
            <div className="flex flex-col items-center justify-center h-64">
              <div className="w-10 h-10 border-3 border-cyan/20 border-t-cyan rounded-full animate-spin" />
              <p className="mt-3 text-secondary text-sm">Loading results...</p>
            </div>
          ) : results.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <div className="w-12 h-12 mb-3 rounded-xl bg-elevated flex items-center justify-center">
                <svg className="w-6 h-6 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h3 className="text-base font-medium text-white mb-1.5">No Results</h3>
              <p className="text-xs text-muted max-w-xs">
                Run a backtest to evaluate historical analysis accuracy
              </p>
            </div>
          ) : (
            <div className="animate-fade-in">
              <div className="overflow-x-auto rounded-xl border border-white/5">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-elevated text-left">
                      <th className="px-3 py-2.5 text-xs font-medium text-secondary uppercase tracking-wider">Code</th>
                      <th className="px-3 py-2.5 text-xs font-medium text-secondary uppercase tracking-wider">Date</th>
                      <th className="px-3 py-2.5 text-xs font-medium text-secondary uppercase tracking-wider">Advice</th>
                      <th className="px-3 py-2.5 text-xs font-medium text-secondary uppercase tracking-wider">Dir.</th>
                      <th className="px-3 py-2.5 text-xs font-medium text-secondary uppercase tracking-wider">Outcome</th>
                      <th className="px-3 py-2.5 text-xs font-medium text-secondary uppercase tracking-wider text-right">Return%</th>
                      <th className="px-3 py-2.5 text-xs font-medium text-secondary uppercase tracking-wider text-center">SL</th>
                      <th className="px-3 py-2.5 text-xs font-medium text-secondary uppercase tracking-wider text-center">TP</th>
                      <th className="px-3 py-2.5 text-xs font-medium text-secondary uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((row) => (
                      <tr
                        key={row.analysisHistoryId}
                        className="border-t border-white/5 hover:bg-hover transition-colors"
                      >
                        <td className="px-3 py-2 font-mono text-cyan text-xs">{row.code}</td>
                        <td className="px-3 py-2 text-xs text-secondary">{row.analysisDate || '--'}</td>
                        <td className="px-3 py-2 text-xs text-white truncate max-w-[140px]" title={row.operationAdvice || ''}>
                          {row.operationAdvice || '--'}
                        </td>
                        <td className="px-3 py-2 text-xs">
                          <span className="flex items-center gap-1">
                            {boolIcon(row.directionCorrect)}
                            <span className="text-muted">{row.directionExpected || ''}</span>
                          </span>
                        </td>
                        <td className="px-3 py-2">{outcomeBadge(row.outcome)}</td>
                        <td className="px-3 py-2 text-xs font-mono text-right">
                          <span className={
                            row.simulatedReturnPct != null
                              ? row.simulatedReturnPct > 0 ? 'text-emerald-400' : row.simulatedReturnPct < 0 ? 'text-red-400' : 'text-secondary'
                              : 'text-muted'
                          }>
                            {pct(row.simulatedReturnPct)}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center">{boolIcon(row.hitStopLoss)}</td>
                        <td className="px-3 py-2 text-center">{boolIcon(row.hitTakeProfit)}</td>
                        <td className="px-3 py-2">{statusBadge(row.evalStatus)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="mt-4">
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                />
              </div>

              <p className="text-xs text-muted text-center mt-2">
                {totalResults} result{totalResults !== 1 ? 's' : ''} total
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default BacktestPage;
